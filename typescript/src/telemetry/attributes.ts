/** Stable harness semantic attributes with conservative redaction. */

import type { HarnessContext } from "./context.ts";

export const TELEMETRY_SCHEMA_VERSION = "1.0.0" as const;

export const SEMANTIC_ATTRIBUTE_KEYS_JSON = '{"correlation_id":"harness.correlation.id","error_type":"error.type","exception_type":"exception.type","harness_id":"harness.id","operation_id":"harness.operation.id","operation_kind":"harness.operation.kind","operation_name":"harness.operation.name","organization_id":"harness.organization.id","outcome":"harness.operation.outcome","plane_id":"harness.plane.id","schema_version":"harness.telemetry.schema.version","tenant_id":"harness.tenant.id"}' as const;

export const SEMANTIC_ATTRIBUTE_KEYS = Object.freeze(
  JSON.parse(SEMANTIC_ATTRIBUTE_KEYS_JSON) as Readonly<Record<string, string>>,
);

export const SENSITIVE_KEY_SEGMENTS = Object.freeze([
  "api_key",
  "authorization",
  "body",
  "completion",
  "content",
  "cookie",
  "credential",
  "message",
  "password",
  "payload",
  "prompt",
  "secret",
  "token",
] as const);

export const OPERATION_KINDS = Object.freeze([
  "INTERNAL",
  "CLIENT",
  "SERVER",
  "PRODUCER",
  "CONSUMER",
] as const);

export type OperationKind = (typeof OPERATION_KINDS)[number];
export type OperationOutcome = "success" | "error";
export type AttributeScalar = string | boolean | number;
export type AttributeValue = AttributeScalar | readonly AttributeScalar[];

export interface SanitizedAttributes {
  readonly values: Readonly<Record<string, AttributeValue>>;
  readonly droppedCount: number;
}

const ATTRIBUTE_KEY = /^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$/;
const OPERATION_NAME = /^[a-z][a-z0-9_.-]{0,127}$/;
const SAFE_STRING = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$/;
const CUSTOM_PREFIX = "harness.label.";
const MAX_ATTRIBUTE_STRING_LENGTH = 256;

export function validateOperationName(value: string): string {
  if (!OPERATION_NAME.test(value)) {
    throw new Error(
      "operation name must be lowercase, non-empty, and at most 128 safe characters",
    );
  }
  return value;
}

export function validateOperationKind(value: string): OperationKind {
  if (!(OPERATION_KINDS as readonly string[]).includes(value)) {
    throw new Error(`unknown operation kind: ${value}`);
  }
  return value as OperationKind;
}

function keyIsSensitive(key: string): boolean {
  const components = new Set(key.split("."));
  const tokens = new Set(key.split(/[._]/));
  return SENSITIVE_KEY_SEGMENTS.some(
    (segment) => components.has(segment) || tokens.has(segment),
  );
}

function keyIsAllowed(key: string): boolean {
  return Object.values(SEMANTIC_ATTRIBUTE_KEYS).includes(key) || key.startsWith(CUSTOM_PREFIX);
}

function sanitizeScalar(value: unknown): AttributeScalar | undefined {
  if (typeof value === "boolean") return value;
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (
    typeof value === "string"
    && value.length <= MAX_ATTRIBUTE_STRING_LENGTH
    && SAFE_STRING.test(value)
  ) return value;
  return undefined;
}

function sanitizeValue(value: unknown): AttributeValue | undefined {
  const scalar = sanitizeScalar(value);
  if (scalar !== undefined) return scalar;
  if (!Array.isArray(value) || value.length === 0) return undefined;
  const accepted = value.map(sanitizeScalar);
  if (accepted.some((item) => item === undefined)) return undefined;
  if (new Set(accepted.map((item) => typeof item)).size !== 1) return undefined;
  return Object.freeze(accepted as AttributeScalar[]);
}

function sortedAttributes(
  input: Readonly<Record<string, AttributeValue>>,
): Record<string, AttributeValue> {
  return Object.fromEntries(
    Object.entries(input).sort(([left], [right]) => (left < right ? -1 : left > right ? 1 : 0)),
  );
}

export function sanitizeAttributes(
  attributes: Readonly<Record<string, unknown>> = {},
): Readonly<SanitizedAttributes> {
  const values: Record<string, AttributeValue> = {};
  let droppedCount = 0;
  for (const [key, value] of Object.entries(attributes).sort(([left], [right]) =>
    left < right ? -1 : left > right ? 1 : 0
  )) {
    if (!ATTRIBUTE_KEY.test(key) || keyIsSensitive(key) || !keyIsAllowed(key)) {
      droppedCount += 1;
      continue;
    }
    const accepted = sanitizeValue(value);
    if (accepted === undefined) {
      droppedCount += 1;
      continue;
    }
    values[key] = accepted;
  }
  return Object.freeze({
    values: Object.freeze(sortedAttributes(values)),
    droppedCount,
  });
}

export function contextAttributes(
  context: HarnessContext,
  operationName: string,
  operationKind: OperationKind,
  outcome: OperationOutcome,
): Readonly<Record<string, AttributeValue>> {
  validateOperationName(operationName);
  validateOperationKind(operationKind);
  const attributes: Record<string, AttributeValue> = {
    [SEMANTIC_ATTRIBUTE_KEYS.schema_version as string]: TELEMETRY_SCHEMA_VERSION,
    [SEMANTIC_ATTRIBUTE_KEYS.operation_name as string]: operationName,
    [SEMANTIC_ATTRIBUTE_KEYS.operation_kind as string]: operationKind,
    [SEMANTIC_ATTRIBUTE_KEYS.outcome as string]: outcome,
  };
  const identityFields = [
    ["tenantId", "tenant_id"],
    ["organizationId", "organization_id"],
    ["harnessId", "harness_id"],
    ["planeId", "plane_id"],
    ["operationId", "operation_id"],
    ["correlationId", "correlation_id"],
  ] as const;
  for (const [field, keyName] of identityFields) {
    const value = context[field];
    const attributeKey = SEMANTIC_ATTRIBUTE_KEYS[keyName];
    if (value !== undefined && attributeKey !== undefined) attributes[attributeKey] = value;
  }
  return Object.freeze(sortedAttributes(attributes));
}
