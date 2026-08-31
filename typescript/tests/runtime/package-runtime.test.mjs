import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { canonicalJson, sha256Digest, verifyReceipt } from "../../dist/runtime/index.js";

const fixtures = new URL("../../../fixtures/runtime/", import.meta.url);
const load = (name) => JSON.parse(readFileSync(new URL(name, fixtures), "utf8"));

test("committed ESM runtime surface verifies the public receipt", async () => {
  const bundle = load("valid-trust-bundle.json");
  const receipt = load("valid-admission-receipt.json");
  assert.match(await sha256Digest(canonicalJson(bundle)), /^sha256:[0-9a-f]{64}$/);
  assert.equal((await verifyReceipt(receipt, bundle, "acme.example", "2030-02-01T00:00:01Z")).admitted, true);
});
