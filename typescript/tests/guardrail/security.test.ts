import assert from "node:assert/strict";
import test from "node:test";

import {
  GuardrailClient,
  GuardrailContractError,
  GuardrailStream,
  canonicalGuardrailResult,
} from "../../src/guardrail/index.ts";


function profile(detectorIds, stage = "INPUT", failMode = "FAIL_CLOSED") {
  return {
    apiVersion: "harness.planeon.ai/v1alpha1",
    kind: "GuardrailProfile",
    profileId: "profile.security",
    version: "1.0.0",
    stage,
    failMode,
    maximumContentBytes: 1024,
    detectorIds,
  };
}

test("detector exceptions cannot leak protected content", () => {
  const detector = {
    detectorId: "detector.throwing",
    evaluate(request) {
      throw new Error(`PRIVATE_EXCEPTION:${request.content}`);
    },
  };
  const privateContent = "PRIVATE_PROTECTED_CONTENT";
  const result = new GuardrailClient(
    profile([detector.detectorId]),
    [detector],
  ).evaluate(privateContent);
  const evidence = canonicalGuardrailResult(result);
  assert.equal(result.outcome, "ERROR_FAIL_CLOSED");
  assert.ok(!evidence.includes(privateContent));
  assert.ok(!evidence.includes("PRIVATE_EXCEPTION"));
});

test("duplicate, missing, and asynchronous detectors fail at construction", () => {
  const allow = {
    detectorId: "detector.allow",
    calls: 0,
    evaluate() {
      this.calls += 1;
      return {
        detectorId: this.detectorId,
        action: "ALLOW",
        reasonCode: "NO_MATCH",
        redactionRanges: [],
      };
    },
  };
  new GuardrailClient(profile([allow.detectorId]), [allow]);
  assert.equal(allow.calls, 0);

  const asynchronous = {
    detectorId: "detector.async",
    async evaluate() {
      throw new Error("PRIVATE_ASYNC");
    },
  };
  for (const [declared, detectors] of [
    [[allow.detectorId], [allow, allow]],
    [[asynchronous.detectorId], [asynchronous]],
    [["detector.missing"], []],
    [[allow.detectorId], [allow, { ...allow, detectorId: "detector.extra" }]],
  ]) {
    assert.throws(
      () => new GuardrailClient(profile(declared), detectors),
      (error) => error instanceof GuardrailContractError && error.code === "UNKNOWN_DETECTOR",
    );
  }
});

test("result shape and finished stream errors are closed", () => {
  const allow = {
    detectorId: "detector.allow",
    evaluate() {
      return {
        detectorId: this.detectorId,
        action: "ALLOW",
        reasonCode: "NO_MATCH",
        redactionRanges: [],
      };
    },
  };
  const result = new GuardrailClient(profile([allow.detectorId]), [allow]).evaluate("PRIVATE");
  assert.deepEqual(Object.keys(result).sort(), [
    "degraded",
    "detectorFindings",
    "failedDetectorIds",
    "outcome",
    "profileId",
    "profileVersion",
    "reasonCode",
    "redactedContent",
    "stage",
  ]);
  assert.ok(!canonicalGuardrailResult(result).includes("PRIVATE"));
  assert.throws(
    () => new GuardrailStream(new GuardrailClient(profile([allow.detectorId]), [allow])),
    (error) => error instanceof GuardrailContractError && error.code === "INVALID_GUARDRAIL_PROFILE",
  );

  const stream = new GuardrailClient(
    profile([allow.detectorId], "STREAMING"),
    [allow],
  ).stream();
  stream.finish();
  assert.throws(
    () => stream.finish(),
    (error) => error instanceof GuardrailContractError && error.code === "STREAM_FINISHED",
  );
});

test("error codes reject inherited object keys", () => {
  assert.throws(
    () => new GuardrailContractError("toString"),
    (error) => error instanceof Error && error.message === "unknown guardrail error code",
  );
});
