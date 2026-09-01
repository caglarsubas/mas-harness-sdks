import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  GuardrailClient,
  GuardrailContractError,
  canonicalGuardrailResult,
} from "../../src/guardrail/index.ts";


const vectors = JSON.parse(
  readFileSync(
    new URL("../../../fixtures/guardrail/conformance-vectors.json", import.meta.url),
    "utf8",
  ),
);

class FixtureDetector {
  constructor(specification) {
    this.detectorId = specification.detectorId;
    this.specification = specification;
    this.calls = 0;
  }

  evaluate(request) {
    this.calls += 1;
    const behavior = this.specification.behavior;
    if (behavior === "THROW") throw new Error("PRIVATE_DETECTOR_EXCEPTION");
    if (behavior === "MALFORMED") {
      return { detectorId: this.detectorId, content: request.content };
    }
    if (behavior === "ALLOW") {
      return {
        detectorId: this.detectorId,
        action: "ALLOW",
        reasonCode: "NO_MATCH",
        redactionRanges: [],
      };
    }
    if (behavior === "ACTION") {
      return {
        detectorId: this.detectorId,
        action: this.specification.action,
        reasonCode: this.specification.reasonCode,
        redactionRanges: this.specification.redactionRanges ?? [],
      };
    }
    assert.equal(behavior, "PATTERN");
    const scalars = Array.from(request.content);
    const pattern = Array.from(this.specification.pattern);
    const ranges = [];
    let index = 0;
    while (index <= scalars.length - pattern.length) {
      if (pattern.every((item, offset) => scalars[index + offset] === item)) {
        ranges.push({ start: index, end: index + pattern.length });
        index += pattern.length;
      } else {
        index += 1;
      }
    }
    if (ranges.length === 0) {
      return {
        detectorId: this.detectorId,
        action: "ALLOW",
        reasonCode: "NO_MATCH",
        redactionRanges: [],
      };
    }
    return {
      detectorId: this.detectorId,
      action: this.specification.action,
      reasonCode: this.specification.reasonCode,
      redactionRanges: this.specification.action === "REDACT" ? ranges : [],
    };
  }
}

function closedError(action, code, privateValue = "") {
  assert.throws(
    action,
    (error) => {
      assert.ok(error instanceof GuardrailContractError);
      assert.equal(error.code, code);
      if (privateValue.length > 0) assert.ok(!String(error).includes(privateValue));
      assert.ok(!String(error).includes("PRIVATE_"));
      return true;
    },
  );
}

function assertResult(result, expected, protectedContent = "") {
  assert.deepEqual(result, expected);
  assert.equal(canonicalGuardrailResult(result), canonicalGuardrailResult(expected));
  if (protectedContent.length > 0) {
    assert.ok(!canonicalGuardrailResult(result).includes(protectedContent));
  }
}

test("shared Python and TypeScript guardrail vectors are exact", () => {
  assert.equal(vectors.schemaVersion, "harness.planeon.ai/guardrail-conformance/v1");
  for (const vector of vectors.vectors) {
    if (vector.kind === "PROFILE_ERROR") {
      closedError(
        () => new GuardrailClient(vector.profile, []),
        vector.expectedError,
        "PRIVATE_PROFILE_FIELD",
      );
      continue;
    }
    const detectors = vector.detectors.map((item) => new FixtureDetector(item));
    const byId = new Map(detectors.map((item) => [item.detectorId, item]));
    if (vector.kind === "CONSTRUCTION_ERROR") {
      closedError(
        () => new GuardrailClient(vector.profile, detectors),
        vector.expectedError,
      );
      assert.ok(detectors.every((item) => item.calls === 0));
      continue;
    }

    const client = new GuardrailClient(vector.profile, detectors);
    assert.ok(detectors.every((item) => item.calls === 0));
    if (vector.kind === "STREAM_CREATION_ERROR") {
      closedError(() => client.stream(), vector.expectedError);
      continue;
    }
    if (vector.kind === "EVALUATE") {
      const result = client.evaluate(vector.content);
      assertResult(result, vector.expectedResult, vector.content);
      if (vector.id === "utf8-byte-limit-before-detector") {
        assert.equal(byId.get("detector.failure").calls, 0);
      }
      continue;
    }

    assert.equal(vector.kind, "STREAM");
    const stream = client.stream();
    let accumulated = "";
    const actual = vector.chunks.map((chunk, index) => {
      accumulated += chunk;
      const result = stream.push(chunk);
      assertResult(result, vector.expectedPushResults[index], accumulated);
      return result;
    });
    assert.deepEqual(actual, vector.expectedPushResults);
    if (vector.finish) {
      assertResult(stream.finish(), vector.expectedFinishResult, accumulated);
    }
    if (vector.afterCall !== undefined) {
      const action = vector.afterCall.method === "PUSH"
        ? () => stream.push(vector.afterCall.value)
        : () => stream.finish();
      closedError(action, vector.expectedError, vector.afterCall.value ?? "");
    }
  }
});

test("expected fixture evidence never repeats complete raw content", () => {
  for (const vector of vectors.vectors) {
    const expected = canonicalGuardrailResult(
      Object.fromEntries(
        Object.entries(vector).filter(([key]) => key.startsWith("expected")),
      ),
    );
    if (typeof vector.content === "string" && vector.content.length > 0) {
      assert.ok(!expected.includes(vector.content), vector.id);
    }
    if (Array.isArray(vector.chunks) && vector.chunks.length > 0) {
      assert.ok(!expected.includes(vector.chunks.join("")), vector.id);
    }
    assert.ok(!expected.includes("PRIVATE_DETECTOR_EXCEPTION"), vector.id);
  }
});
