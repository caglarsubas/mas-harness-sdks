import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  canonicalJson,
  createContext,
  extractContext,
  injectContext,
  instrumentAsync,
  instrumentSync,
  sanitizeAttributes,
  type HarnessContext,
  type SpanRecord,
} from "../../src/telemetry/index.ts";

const EXPECTED_VECTOR_IDS = Object.freeze([
  "sync-error-redacts-credentials",
  "sync-success-redacts-content",
]);

interface VectorInput {
  readonly attributes: Readonly<Record<string, unknown>>;
  readonly clock: readonly number[];
  readonly errorType?: string;
  readonly operationKind: "INTERNAL" | "CLIENT" | "SERVER" | "PRODUCER" | "CONSUMER";
  readonly operationName: string;
  readonly spanId: string;
}

interface GoldenVector {
  readonly id: string;
  readonly input: VectorInput;
  readonly expected: Readonly<Record<string, unknown>>;
}

interface VectorDocument {
  readonly parentContext: HarnessContext;
  readonly vectors: readonly GoldenVector[];
}

const vectorsUrl = new URL("../../../examples/telemetry/golden-span-vectors.json", import.meta.url);
const document = JSON.parse(readFileSync(vectorsUrl, "utf8")) as VectorDocument;

function sequenceClock(values: readonly number[]): () => string {
  let index = 0;
  return () => {
    const value = values[index];
    index += 1;
    if (value === undefined) throw new Error("golden clock exhausted");
    return value.toString();
  };
}

test("TypeScript matches every cross-language golden vector", () => {
  assert.deepEqual(
    document.vectors.map((vector) => vector.id).sort(),
    [...EXPECTED_VECTOR_IDS],
  );
  const parent = createContext(document.parentContext);
  for (const vector of document.vectors) {
    const records: SpanRecord[] = [];
    const operation = instrumentSync(
      vector.input.operationName,
      () => {
        if (vector.input.errorType !== undefined) {
          throw new Error("fixture-message-that-must-not-be-exported");
        }
        return "accepted";
      },
      {
        operationKind: vector.input.operationKind,
        attributes: vector.input.attributes,
        clockUnixNano: sequenceClock(vector.input.clock),
        traceIdFactory: () => "11111111111111111111111111111111",
        spanIdFactory: () => vector.input.spanId,
        errorType: () => vector.input.errorType ?? "error",
        sink: (record) => records.push(record),
      },
    );
    try {
      operation(parent);
    } catch (error) {
      if (vector.input.errorType === undefined) throw error;
    }
    assert.equal(records.length, 1, vector.id);
    assert.equal(canonicalJson(records[0]), canonicalJson(vector.expected), vector.id);
    assert.doesNotMatch(canonicalJson(records[0]), /fixture-message-that-must-not-be-exported/);
  }
});

test("carrier identity remains untrusted by default", () => {
  const context = createContext(document.parentContext);
  const carrier = injectContext(context, {}, true);
  assert.equal(extractContext(carrier)?.tenantId, undefined);
  assert.equal(extractContext(carrier, { trustIdentity: true, strict: true })?.tenantId, "tenant-a");
});

test("sensitive and unknown attributes are dropped without their values", () => {
  const sanitized = sanitizeAttributes({
    "harness.label.accepted": "yes",
    "harness.label.note": "free text is not an opaque label",
    "harness.label.raw_prompt": "fixture-secret-that-must-not-be-exported",
    "harness.label.api_key": "fixture-key-that-must-not-be-exported",
    "gen_ai.prompt": "fixture-secret-that-must-not-be-exported",
    "other.value": "unknown-value-that-must-not-be-exported",
  });
  assert.deepEqual(sanitized.values, { "harness.label.accepted": "yes" });
  assert.equal(sanitized.droppedCount, 5);
  assert.doesNotMatch(
    JSON.stringify(sanitized),
    /fixture-secret|fixture-key|free text|unknown-value|raw_prompt|api_key|gen_ai/,
  );
});

test("strict sink errors never mask a business failure", () => {
  const context = createContext(document.parentContext);
  const operation = instrumentSync(
    "harness.business.fail",
    () => {
      throw new Error("business failure");
    },
    {
      traceIdFactory: () => "11111111111111111111111111111111",
      spanIdFactory: () => "1111111111111111",
      clockUnixNano: sequenceClock([1, 2]),
      strictSink: true,
      sink: () => {
        throw new Error("sink unavailable");
      },
    },
  );
  assert.throws(() => operation(context), /business failure/);
});

test("strict sink errors on success remain sink errors", () => {
  const context = createContext(document.parentContext);
  const operation = instrumentSync(
    "harness.sink.strict",
    () => "business-result",
    {
      traceIdFactory: () => "11111111111111111111111111111111",
      spanIdFactory: () => "1111111111111111",
      clockUnixNano: sequenceClock([1, 2]),
      strictSink: true,
      sink: () => {
        throw new Error("sink unavailable");
      },
    },
  );
  assert.throws(() => operation(context), /sink unavailable/);
});

test("classifier failures never mask business failures", () => {
  const context = createContext(document.parentContext);
  const records: SpanRecord[] = [];
  const operation = instrumentSync(
    "harness.classifier.fail",
    () => {
      throw new Error("business failure");
    },
    {
      traceIdFactory: () => "11111111111111111111111111111111",
      spanIdFactory: () => "1111111111111111",
      clockUnixNano: sequenceClock([1, 2]),
      errorType: () => {
        throw new Error("classifier failure");
      },
      sink: (record) => records.push(record),
    },
  );
  assert.throws(() => operation(context), /business failure/);
  assert.equal(records[0]?.attributes["error.type"], "error");
});

test("instrumentation creates cryptographic IDs without injected factories", () => {
  const records: SpanRecord[] = [];
  const operation = instrumentSync(
    "harness.ids.create",
    () => "accepted",
    { clockUnixNano: sequenceClock([1, 2]), sink: (record) => records.push(record) },
  );
  assert.equal(operation(undefined), "accepted");
  assert.match(records[0]?.traceId ?? "", /^[0-9a-f]{32}$/);
  assert.match(records[0]?.spanId ?? "", /^[0-9a-f]{16}$/);
});

test("async instrumentation passes an explicit child context", async () => {
  const context = createContext(document.parentContext);
  const records: SpanRecord[] = [];
  const operation = instrumentAsync(
    "harness.async.execute",
    async (active) => active.spanId,
    {
      operationKind: "CLIENT",
      traceIdFactory: () => "11111111111111111111111111111111",
      spanIdFactory: () => "3333333333333333",
      clockUnixNano: sequenceClock([10, 20]),
      sink: (record) => records.push(record),
    },
  );
  assert.equal(await operation(context), "3333333333333333");
  assert.equal(records[0]?.kind, "CLIENT");
  assert.equal(records[0]?.parentSpanId, context.spanId);
});
