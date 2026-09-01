import assert from "node:assert/strict";
import test from "node:test";

import {
  GuardrailClient,
  canonicalGuardrailResult,
} from "../../dist/guardrail/index.js";


test("committed package guardrail surface evaluates locally", () => {
  const detector = {
    detectorId: "detector.package",
    evaluate() {
      return {
        detectorId: this.detectorId,
        action: "ALLOW",
        reasonCode: "NO_MATCH",
        redactionRanges: [],
      };
    },
  };
  const client = new GuardrailClient(
    {
      apiVersion: "harness.planeon.ai/v1alpha1",
      kind: "GuardrailProfile",
      profileId: "profile.package",
      version: "1.0.0",
      stage: "INPUT",
      failMode: "FAIL_CLOSED",
      maximumContentBytes: 1024,
      detectorIds: [detector.detectorId],
    },
    [detector],
  );
  const result = client.evaluate("PRIVATE_PACKAGE_CONTENT");
  assert.equal(result.outcome, "ALLOW");
  assert.ok(!canonicalGuardrailResult(result).includes("PRIVATE_PACKAGE_CONTENT"));
});
