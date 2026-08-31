/** Tenant-neutral context and strict W3C traceparent propagation. */

export const TRACEPARENT_HEADER = "traceparent" as const;

export const IDENTITY_HEADERS = Object.freeze({
  tenantId: "x-harness-tenant-id",
  organizationId: "x-harness-organization-id",
  harnessId: "x-harness-harness-id",
  planeId: "x-harness-plane-id",
  operationId: "x-harness-operation-id",
  correlationId: "x-harness-correlation-id",
} as const);

const TRACE_ID = /^[0-9a-f]{32}$/;
const SPAN_ID = /^[0-9a-f]{16}$/;
const TRACE_FLAGS = /^[0-9a-f]{2}$/;
const OPAQUE_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;

export interface HarnessContext {
  readonly traceId: string;
  readonly spanId: string;
  readonly traceFlags: string;
  readonly tenantId?: string;
  readonly organizationId?: string;
  readonly harnessId?: string;
  readonly planeId?: string;
  readonly operationId?: string;
  readonly correlationId?: string;
}

export class ContextValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ContextValidationError";
  }
}

function validateTraceId(value: string): string {
  if (!TRACE_ID.test(value) || value === "0".repeat(32)) {
    throw new ContextValidationError(
      "traceId must be 32 lowercase non-zero hexadecimal characters",
    );
  }
  return value;
}

function validateSpanId(value: string): string {
  if (!SPAN_ID.test(value) || value === "0".repeat(16)) {
    throw new ContextValidationError(
      "spanId must be 16 lowercase non-zero hexadecimal characters",
    );
  }
  return value;
}

function validateTraceFlags(value: string): string {
  if (!TRACE_FLAGS.test(value)) {
    throw new ContextValidationError(
      "traceFlags must be two lowercase hexadecimal characters",
    );
  }
  return value;
}

function validateOpaqueId(name: string, value: string | undefined): string | undefined {
  if (value === undefined) return undefined;
  if (!OPAQUE_ID.test(value)) {
    throw new ContextValidationError(
      `${name} must be an opaque 1-128 character identifier without whitespace`,
    );
  }
  return value;
}

export function createContext(input: HarnessContext): Readonly<HarnessContext> {
  const context: HarnessContext = {
    traceId: validateTraceId(input.traceId),
    spanId: validateSpanId(input.spanId),
    traceFlags: validateTraceFlags(input.traceFlags),
    tenantId: validateOpaqueId("tenantId", input.tenantId),
    organizationId: validateOpaqueId("organizationId", input.organizationId),
    harnessId: validateOpaqueId("harnessId", input.harnessId),
    planeId: validateOpaqueId("planeId", input.planeId),
    operationId: validateOpaqueId("operationId", input.operationId),
    correlationId: validateOpaqueId("correlationId", input.correlationId),
  };
  return Object.freeze(context);
}

export function childContext(
  parent: HarnessContext,
  spanId: string,
): Readonly<HarnessContext> {
  return createContext({ ...parent, spanId });
}

export function formatTraceparent(context: HarnessContext): string {
  return `00-${context.traceId}-${context.spanId}-${context.traceFlags}`;
}

export function parseTraceparent(
  value: string,
): Readonly<{ traceId: string; spanId: string; traceFlags: string }> {
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

function normalizeCarrier(carrier: Readonly<Record<string, string>>): Record<string, string> {
  const normalized: Record<string, string> = {};
  for (const [rawName, value] of Object.entries(carrier)) {
    const name = rawName.toLowerCase();
    if (Object.hasOwn(normalized, name)) {
      throw new ContextValidationError(
        `carrier contains a case-insensitive duplicate: ${name}`,
      );
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

function sortedRecord(input: Readonly<Record<string, string>>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(input).sort(([left], [right]) => (left < right ? -1 : left > right ? 1 : 0)),
  );
}

export function injectContext(
  context: HarnessContext,
  carrier: Readonly<Record<string, string>> = {},
  includeIdentity = false,
): Readonly<Record<string, string>> {
  const result = normalizeCarrier(carrier);
  result[TRACEPARENT_HEADER] = formatTraceparent(context);
  if (includeIdentity) {
    for (const [field, header] of Object.entries(IDENTITY_HEADERS)) {
      const value = context[field as keyof HarnessContext];
      if (typeof value === "string") result[header] = value;
    }
  }
  return Object.freeze(sortedRecord(result));
}

export function extractContext(
  carrier: Readonly<Record<string, string>>,
  options: Readonly<{ trustIdentity?: boolean; strict?: boolean }> = {},
): Readonly<HarnessContext> | undefined {
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
