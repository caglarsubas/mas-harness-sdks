/** Explicit-context sync and async instrumentation with a no-op default sink. */

import {
  SEMANTIC_ATTRIBUTE_KEYS,
  contextAttributes,
  sanitizeAttributes,
  validateOperationKind,
  validateOperationName,
  type AttributeValue,
  type OperationKind,
  type OperationOutcome,
} from "./attributes.ts";
import { childContext, createContext, type HarnessContext } from "./context.ts";

export const SPAN_SCHEMA_VERSION = "harness.telemetry.span/v1" as const;

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

const NULL_SINK: SpanSink = () => undefined;

function defaultClock(): string {
  return (BigInt(Date.now()) * 1_000_000n).toString();
}

function defaultErrorType(error: unknown): string {
  if (error instanceof Error && error.name) {
    return error.name
      .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
      .replace(/[^A-Za-z0-9_.-]/g, "_")
      .toLowerCase();
  }
  return "error";
}

function randomHex(byteLength: number): string {
  const values = new Uint8Array(byteLength);
  globalThis.crypto.getRandomValues(values);
  return Array.from(values, (value) => value.toString(16).padStart(2, "0")).join("");
}

function classifyError(options: InstrumentOptions, error: unknown): string {
  try {
    const value = (options.errorType ?? defaultErrorType)(error);
    return typeof value === "string" ? value : "error";
  } catch {
    return "error";
  }
}

function sortedAttributes(
  input: Readonly<Record<string, AttributeValue>>,
): Record<string, AttributeValue> {
  return Object.fromEntries(
    Object.entries(input).sort(([left], [right]) => (left < right ? -1 : left > right ? 1 : 0)),
  );
}

function buildRecord(
  operationName: string,
  operationKind: OperationKind,
  context: HarnessContext,
  parentSpanId: string | null,
  startTimeUnixNano: string,
  endTimeUnixNano: string,
  outcome: OperationOutcome,
  extraAttributes: Readonly<Record<string, unknown>> | undefined,
  errorType: string | undefined,
): Readonly<SpanRecord> {
  const attributes: Record<string, AttributeValue> = {
    ...contextAttributes(context, operationName, operationKind, outcome),
  };
  const sanitized = sanitizeAttributes(extraAttributes);
  Object.assign(attributes, sanitized.values);
  let events: readonly SpanEvent[] = [];
  if (errorType !== undefined) {
    const safeError = sanitizeAttributes({
      [SEMANTIC_ATTRIBUTE_KEYS.error_type as string]: errorType,
    });
    const safeException = sanitizeAttributes({
      [SEMANTIC_ATTRIBUTE_KEYS.exception_type as string]: errorType,
    });
    Object.assign(attributes, safeError.values);
    events = Object.freeze([
      Object.freeze({
        name: "exception" as const,
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
    attributes: Object.freeze(sortedAttributes(attributes)),
    events,
    droppedAttributesCount: sanitized.droppedCount,
  });
}

function emit(options: InstrumentOptions, record: Readonly<SpanRecord>): void {
  try {
    (options.sink ?? NULL_SINK)(record);
  } catch (error) {
    if (options.strictSink) throw error;
  }
}

function activeContext(
  parent: HarnessContext | undefined,
  options: InstrumentOptions,
): Readonly<HarnessContext> {
  return parent === undefined
    ? createContext({
        traceId: options.traceIdFactory?.() ?? randomHex(16),
        spanId: options.spanIdFactory?.() ?? randomHex(8),
        traceFlags: "00",
      })
    : childContext(parent, options.spanIdFactory?.() ?? randomHex(8));
}

export function instrumentSync<Arguments extends unknown[], Result>(
  operationName: string,
  operation: (context: HarnessContext, ...args: Arguments) => Result,
  options: InstrumentOptions,
): (parent: HarnessContext | undefined, ...args: Arguments) => Result {
  validateOperationName(operationName);
  const operationKind = validateOperationKind(options.operationKind ?? "INTERNAL");
  return (parent: HarnessContext | undefined, ...args: Arguments): Result => {
    const active = activeContext(parent, options);
    const clock = options.clockUnixNano ?? defaultClock;
    const started = clock();
    let result: Result;
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

export function instrumentAsync<Arguments extends unknown[], Result>(
  operationName: string,
  operation: (context: HarnessContext, ...args: Arguments) => Promise<Result>,
  options: InstrumentOptions,
): (parent: HarnessContext | undefined, ...args: Arguments) => Promise<Result> {
  validateOperationName(operationName);
  const operationKind = validateOperationKind(options.operationKind ?? "INTERNAL");
  return async (parent: HarnessContext | undefined, ...args: Arguments): Promise<Result> => {
    const active = activeContext(parent, options);
    const clock = options.clockUnixNano ?? defaultClock;
    const started = clock();
    let result: Result;
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
