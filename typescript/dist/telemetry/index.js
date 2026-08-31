/** Dependency-free tenant-neutral telemetry runtime. */

export const TRACEPARENT_HEADER = "traceparent";
export const IDENTITY_HEADERS = Object.freeze({
  tenantId: "x-harness-tenant-id",
  organizationId: "x-harness-organization-id",
  harnessId: "x-harness-harness-id",
  planeId: "x-harness-plane-id",
  operationId: "x-harness-operation-id",
  correlationId: "x-harness-correlation-id",
});
export const TELEMETRY_SCHEMA_VERSION = "1.0.0";
export const SPAN_SCHEMA_VERSION = "harness.telemetry.span/v1";
export const SEMANTIC_ATTRIBUTE_KEYS_JSON = '{"correlation_id":"harness.correlation.id","error_type":"error.type","exception_type":"exception.type","harness_id":"harness.id","operation_id":"harness.operation.id","operation_kind":"harness.operation.kind","operation_name":"harness.operation.name","organization_id":"harness.organization.id","outcome":"harness.operation.outcome","plane_id":"harness.plane.id","schema_version":"harness.telemetry.schema.version","tenant_id":"harness.tenant.id"}';
export const SEMANTIC_ATTRIBUTE_KEYS = Object.freeze(JSON.parse(SEMANTIC_ATTRIBUTE_KEYS_JSON));
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
]);
export const OPERATION_KINDS = Object.freeze([
  "INTERNAL",
  "CLIENT",
  "SERVER",
  "PRODUCER",
  "CONSUMER",
]);

const TRACE_ID = /^[0-9a-f]{32}$/;
const SPAN_ID = /^[0-9a-f]{16}$/;
const TRACE_FLAGS = /^[0-9a-f]{2}$/;
const OPAQUE_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
const ATTRIBUTE_KEY = /^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$/;
const OPERATION_NAME = /^[a-z][a-z0-9_.-]{0,127}$/;
const SAFE_STRING = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$/;
const CUSTOM_PREFIX = "harness.label.";
const MAX_ATTRIBUTE_STRING_LENGTH = 256;
const NULL_SINK = () => undefined;

export class ContextValidationError extends Error {
  constructor(message) {
    super(message);
    this.name = "ContextValidationError";
  }
}

function compareKeys(left, right) {
  return left < right ? -1 : left > right ? 1 : 0;
}

function sortedRecord(input) {
  return Object.fromEntries(Object.entries(input).sort(([left], [right]) => compareKeys(left, right)));
}

function validateTraceId(value) {
  if (!TRACE_ID.test(value) || value === "0".repeat(32)) {
    throw new ContextValidationError("traceId must be 32 lowercase non-zero hexadecimal characters");
  }
  return value;
}

function validateSpanId(value) {
  if (!SPAN_ID.test(value) || value === "0".repeat(16)) {
    throw new ContextValidationError("spanId must be 16 lowercase non-zero hexadecimal characters");
  }
  return value;
}

function validateTraceFlags(value) {
  if (!TRACE_FLAGS.test(value)) {
    throw new ContextValidationError("traceFlags must be two lowercase hexadecimal characters");
  }
  return value;
}

function validateOpaqueId(name, value) {
  if (value === undefined) return undefined;
  if (typeof value !== "string" || !OPAQUE_ID.test(value)) {
    throw new ContextValidationError(
      `${name} must be an opaque 1-128 character identifier without whitespace`,
    );
  }
  return value;
}

export function createContext(input) {
  return Object.freeze({
    traceId: validateTraceId(input.traceId),
    spanId: validateSpanId(input.spanId),
    traceFlags: validateTraceFlags(input.traceFlags),
    tenantId: validateOpaqueId("tenantId", input.tenantId),
    organizationId: validateOpaqueId("organizationId", input.organizationId),
    harnessId: validateOpaqueId("harnessId", input.harnessId),
    planeId: validateOpaqueId("planeId", input.planeId),
    operationId: validateOpaqueId("operationId", input.operationId),
    correlationId: validateOpaqueId("correlationId", input.correlationId),
  });
}

export function childContext(parent, spanId) {
  return createContext({ ...parent, spanId });
}

export function formatTraceparent(context) {
  return `00-${context.traceId}-${context.spanId}-${context.traceFlags}`;
}

export function parseTraceparent(value) {
  const parts = value.split("-");
  if (parts.length !== 4 || parts[0] !== "00") {
    throw new ContextValidationError(
      "only the four-field W3C traceparent version 00 is supported",
    );
  }
  return Object.freeze({
    traceId: validateTraceId(parts[1] ?? ""),
    spanId: validateSpanId(parts[2] ?? ""),
    traceFlags: validateTraceFlags(parts[3] ?? ""),
  });
}

function normalizeCarrier(carrier) {
  const normalized = {};
  for (const [rawName, value] of Object.entries(carrier)) {
    const name = rawName.toLowerCase();
    if (Object.hasOwn(normalized, name)) {
      throw new ContextValidationError(`carrier contains a case-insensitive duplicate: ${name}`);
    }
    if (typeof value !== "string") {
      throw new ContextValidationError("carrier names and values must be strings");
    }
    if (value.includes("\r") || value.includes("\n")) {
      throw new ContextValidationError(`carrier value contains a line break: ${name}`);
    }
    normalized[name] = value;
  }
  return normalized;
}

export function injectContext(context, carrier = {}, includeIdentity = false) {
  const result = normalizeCarrier(carrier);
  result[TRACEPARENT_HEADER] = formatTraceparent(context);
  if (includeIdentity) {
    for (const [field, header] of Object.entries(IDENTITY_HEADERS)) {
      const value = context[field];
      if (typeof value === "string") result[header] = value;
    }
  }
  return Object.freeze(sortedRecord(result));
}

export function extractContext(carrier, options = {}) {
  try {
    const normalized = normalizeCarrier(carrier);
    const value = normalized[TRACEPARENT_HEADER];
    if (value === undefined) return undefined;
    const trace = parseTraceparent(value);
    const identity = options.trustIdentity
      ? Object.fromEntries(
          Object.entries(IDENTITY_HEADERS)
            .filter(([, header]) => normalized[header] !== undefined)
            .map(([field, header]) => [field, normalized[header]]),
        )
      : {};
    return createContext({ ...trace, ...identity });
  } catch (error) {
    if (options.strict) throw error;
    return undefined;
  }
}

export function validateOperationName(value) {
  if (!OPERATION_NAME.test(value)) {
    throw new Error("operation name must be lowercase, non-empty, and at most 128 safe characters");
  }
  return value;
}

export function validateOperationKind(value) {
  if (!OPERATION_KINDS.includes(value)) throw new Error(`unknown operation kind: ${value}`);
  return value;
}

function keyIsSensitive(key) {
  const components = new Set(key.split("."));
  const tokens = new Set(key.split(/[._]/));
  return SENSITIVE_KEY_SEGMENTS.some(
    (segment) => components.has(segment) || tokens.has(segment),
  );
}

function keyIsAllowed(key) {
  return Object.values(SEMANTIC_ATTRIBUTE_KEYS).includes(key) || key.startsWith(CUSTOM_PREFIX);
}

function sanitizeScalar(value) {
  if (typeof value === "boolean") return value;
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (
    typeof value === "string"
    && value.length <= MAX_ATTRIBUTE_STRING_LENGTH
    && SAFE_STRING.test(value)
  ) return value;
  return undefined;
}

function sanitizeValue(value) {
  const scalar = sanitizeScalar(value);
  if (scalar !== undefined) return scalar;
  if (!Array.isArray(value) || value.length === 0) return undefined;
  const accepted = value.map(sanitizeScalar);
  if (accepted.some((item) => item === undefined)) return undefined;
  if (new Set(accepted.map((item) => typeof item)).size !== 1) return undefined;
  return Object.freeze(accepted);
}

export function sanitizeAttributes(attributes = {}) {
  const values = {};
  let droppedCount = 0;
  for (const [key, value] of Object.entries(attributes).sort(([left], [right]) => compareKeys(left, right))) {
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
    values: Object.freeze(sortedRecord(values)),
    droppedCount,
  });
}

export function contextAttributes(context, operationName, operationKind, outcome) {
  validateOperationName(operationName);
  validateOperationKind(operationKind);
  if (outcome !== "success" && outcome !== "error") {
    throw new Error(`unknown operation outcome: ${outcome}`);
  }
  const attributes = {
    [SEMANTIC_ATTRIBUTE_KEYS.schema_version]: TELEMETRY_SCHEMA_VERSION,
    [SEMANTIC_ATTRIBUTE_KEYS.operation_name]: operationName,
    [SEMANTIC_ATTRIBUTE_KEYS.operation_kind]: operationKind,
    [SEMANTIC_ATTRIBUTE_KEYS.outcome]: outcome,
  };
  const identityFields = [
    ["tenantId", "tenant_id"],
    ["organizationId", "organization_id"],
    ["harnessId", "harness_id"],
    ["planeId", "plane_id"],
    ["operationId", "operation_id"],
    ["correlationId", "correlation_id"],
  ];
  for (const [field, keyName] of identityFields) {
    const value = context[field];
    const attributeKey = SEMANTIC_ATTRIBUTE_KEYS[keyName];
    if (value !== undefined && attributeKey !== undefined) attributes[attributeKey] = value;
  }
  return Object.freeze(sortedRecord(attributes));
}

function canonicalValue(value) {
  if (value === null || typeof value === "string" || typeof value === "boolean") return value;
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new Error("canonical telemetry JSON forbids non-finite numbers");
    return value;
  }
  if (Array.isArray(value)) return value.map(canonicalValue);
  if (typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value)
        .sort(([left], [right]) => compareKeys(left, right))
        .map(([key, item]) => [key, canonicalValue(item)]),
    );
  }
  throw new Error(`canonical telemetry JSON forbids ${typeof value}`);
}

export function canonicalJson(value) {
  return JSON.stringify(canonicalValue(value));
}

function defaultClock() {
  return (BigInt(Date.now()) * 1_000_000n).toString();
}

function defaultErrorType(error) {
  if (error instanceof Error && error.name) {
    return error.name
      .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
      .replace(/[^A-Za-z0-9_.-]/g, "_")
      .toLowerCase();
  }
  return "error";
}

function randomHex(byteLength) {
  const values = new Uint8Array(byteLength);
  globalThis.crypto.getRandomValues(values);
  return Array.from(values, (value) => value.toString(16).padStart(2, "0")).join("");
}

function classifyError(options, error) {
  try {
    const value = (options.errorType ?? defaultErrorType)(error);
    return typeof value === "string" ? value : "error";
  } catch {
    return "error";
  }
}

function buildRecord(
  operationName,
  operationKind,
  context,
  parentSpanId,
  startTimeUnixNano,
  endTimeUnixNano,
  outcome,
  extraAttributes,
  errorType,
) {
  const attributes = { ...contextAttributes(context, operationName, operationKind, outcome) };
  const sanitized = sanitizeAttributes(extraAttributes);
  Object.assign(attributes, sanitized.values);
  let events = [];
  if (errorType !== undefined) {
    const safeError = sanitizeAttributes({ [SEMANTIC_ATTRIBUTE_KEYS.error_type]: errorType });
    const safeException = sanitizeAttributes({
      [SEMANTIC_ATTRIBUTE_KEYS.exception_type]: errorType,
    });
    Object.assign(attributes, safeError.values);
    events = Object.freeze([
      Object.freeze({
        name: "exception",
        timeUnixNano: endTimeUnixNano,
        attributes: safeException.values,
      }),
    ]);
  }
  return Object.freeze({
    schemaVersion: SPAN_SCHEMA_VERSION,
    name: operationName,
    kind: operationKind,
    traceId: context.traceId,
    spanId: context.spanId,
    parentSpanId,
    traceFlags: context.traceFlags,
    startTimeUnixNano,
    endTimeUnixNano,
    status: Object.freeze({ code: outcome === "error" ? "ERROR" : "OK" }),
    attributes: Object.freeze(sortedRecord(attributes)),
    events,
    droppedAttributesCount: sanitized.droppedCount,
  });
}

function emit(options, record) {
  try {
    (options.sink ?? NULL_SINK)(record);
  } catch (error) {
    if (options.strictSink) throw error;
  }
}

function activeContext(parent, options) {
  return parent === undefined
    ? createContext({
        traceId: options.traceIdFactory?.() ?? randomHex(16),
        spanId: options.spanIdFactory?.() ?? randomHex(8),
        traceFlags: "00",
      })
    : childContext(parent, options.spanIdFactory?.() ?? randomHex(8));
}

export function instrumentSync(operationName, operation, options) {
  validateOperationName(operationName);
  const operationKind = validateOperationKind(options.operationKind ?? "INTERNAL");
  return (parent, ...args) => {
    const active = activeContext(parent, options);
    const clock = options.clockUnixNano ?? defaultClock;
    const started = clock();
    let result;
    try {
      result = operation(active, ...args);
    } catch (error) {
      const ended = clock();
      emit(
        { ...options, strictSink: false },
        buildRecord(
          operationName,
          operationKind,
          active,
          parent?.spanId ?? null,
          started,
          ended,
          "error",
          options.attributes,
          classifyError(options, error),
        ),
      );
      throw error;
    }
    const ended = clock();
    emit(
      options,
      buildRecord(
        operationName,
        operationKind,
        active,
        parent?.spanId ?? null,
        started,
        ended,
        "success",
        options.attributes,
        undefined,
      ),
    );
    return result;
  };
}

export function instrumentAsync(operationName, operation, options) {
  validateOperationName(operationName);
  const operationKind = validateOperationKind(options.operationKind ?? "INTERNAL");
  return async (parent, ...args) => {
    const active = activeContext(parent, options);
    const clock = options.clockUnixNano ?? defaultClock;
    const started = clock();
    let result;
    try {
      result = await operation(active, ...args);
    } catch (error) {
      const ended = clock();
      emit(
        { ...options, strictSink: false },
        buildRecord(
          operationName,
          operationKind,
          active,
          parent?.spanId ?? null,
          started,
          ended,
          "error",
          options.attributes,
          classifyError(options, error),
        ),
      );
      throw error;
    }
    const ended = clock();
    emit(
      options,
      buildRecord(
        operationName,
        operationKind,
        active,
        parent?.spanId ?? null,
        started,
        ended,
        "success",
        options.attributes,
        undefined,
      ),
    );
    return result;
  };
}
