export declare const TRACEPARENT_HEADER: "traceparent";
export declare const IDENTITY_HEADERS: Readonly<{
  tenantId: "x-harness-tenant-id";
  organizationId: "x-harness-organization-id";
  harnessId: "x-harness-harness-id";
  planeId: "x-harness-plane-id";
  operationId: "x-harness-operation-id";
  correlationId: "x-harness-correlation-id";
}>;
export declare const TELEMETRY_SCHEMA_VERSION: "1.0.0";
export declare const SPAN_SCHEMA_VERSION: "harness.telemetry.span/v1";
export declare const SEMANTIC_ATTRIBUTE_KEYS_JSON: string;
export declare const SEMANTIC_ATTRIBUTE_KEYS: Readonly<Record<string, string>>;
export declare const SENSITIVE_KEY_SEGMENTS: readonly string[];
export declare const OPERATION_KINDS: readonly [
  "INTERNAL",
  "CLIENT",
  "SERVER",
  "PRODUCER",
  "CONSUMER",
];

export type OperationKind = (typeof OPERATION_KINDS)[number];
export type OperationOutcome = "success" | "error";
export type AttributeScalar = string | boolean | number;
export type AttributeValue = AttributeScalar | readonly AttributeScalar[];

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

export interface SanitizedAttributes {
  readonly values: Readonly<Record<string, AttributeValue>>;
  readonly droppedCount: number;
}

export interface SpanEvent {
  readonly name: "exception";
  readonly timeUnixNano: string;
  readonly attributes: Readonly<Record<string, AttributeValue>>;
}

export interface SpanRecord {
  readonly schemaVersion: typeof SPAN_SCHEMA_VERSION;
  readonly name: string;
  readonly kind: OperationKind;
  readonly traceId: string;
  readonly spanId: string;
  readonly parentSpanId: string | null;
  readonly traceFlags: string;
  readonly startTimeUnixNano: string;
  readonly endTimeUnixNano: string;
  readonly status: Readonly<{ code: "OK" | "ERROR" }>;
  readonly attributes: Readonly<Record<string, AttributeValue>>;
  readonly events: readonly SpanEvent[];
  readonly droppedAttributesCount: number;
}

export type SpanSink = (record: Readonly<SpanRecord>) => void;

export interface InstrumentOptions {
  readonly operationKind?: OperationKind;
  readonly attributes?: Readonly<Record<string, unknown>>;
  readonly sink?: SpanSink;
  readonly clockUnixNano?: () => string;
  readonly traceIdFactory?: () => string;
  readonly spanIdFactory?: () => string;
  readonly errorType?: (error: unknown) => string;
  readonly strictSink?: boolean;
}

export declare class ContextValidationError extends Error {}
export declare function createContext(input: HarnessContext): Readonly<HarnessContext>;
export declare function childContext(
  parent: HarnessContext,
  spanId: string,
): Readonly<HarnessContext>;
export declare function formatTraceparent(context: HarnessContext): string;
export declare function parseTraceparent(value: string): Readonly<{
  traceId: string;
  spanId: string;
  traceFlags: string;
}>;
export declare function injectContext(
  context: HarnessContext,
  carrier?: Readonly<Record<string, string>>,
  includeIdentity?: boolean,
): Readonly<Record<string, string>>;
export declare function extractContext(
  carrier: Readonly<Record<string, string>>,
  options?: Readonly<{ trustIdentity?: boolean; strict?: boolean }>,
): Readonly<HarnessContext> | undefined;
export declare function validateOperationName(value: string): string;
export declare function validateOperationKind(value: string): OperationKind;
export declare function sanitizeAttributes(
  attributes?: Readonly<Record<string, unknown>>,
): Readonly<SanitizedAttributes>;
export declare function contextAttributes(
  context: HarnessContext,
  operationName: string,
  operationKind: OperationKind,
  outcome: OperationOutcome,
): Readonly<Record<string, AttributeValue>>;
export declare function canonicalJson(value: unknown): string;
export declare function instrumentSync<Arguments extends unknown[], Result>(
  operationName: string,
  operation: (context: HarnessContext, ...args: Arguments) => Result,
  options: InstrumentOptions,
): (parent: HarnessContext | undefined, ...args: Arguments) => Result;
export declare function instrumentAsync<Arguments extends unknown[], Result>(
  operationName: string,
  operation: (context: HarnessContext, ...args: Arguments) => Promise<Result>,
  options: InstrumentOptions,
): (parent: HarnessContext | undefined, ...args: Arguments) => Promise<Result>;
