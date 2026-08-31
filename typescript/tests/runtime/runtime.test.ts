import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  canonicalJson,
  parseJsonStrict,
  replayDigests,
  sha256Digest,
  signedMessage,
  verifyAdmission,
  verifyBootstrapBundle,
  verifyReceipt,
  verifyRotatedBundle,
  type AtomicReplayStore,
  type ReplayReservation,
} from "../../src/runtime/index.ts";

const fixtures = new URL("../../../fixtures/runtime/", import.meta.url);
const load = (name: string): Record<string, unknown> => JSON.parse(readFileSync(new URL(name, fixtures), "utf8")) as Record<string, unknown>;
const clone = <T>(value: T): T => structuredClone(value);
const limits = Object.freeze({maxConcurrentTasks: 4, maxTaskSeconds: 300, maxRetries: 2, maxToolCalls: 20, maxModelTokens: 4096});
const observed = Object.freeze({concurrentTasks: 4, taskSeconds: 300, retries: 2, toolCalls: 20, modelTokens: 4096});

class Store implements AtomicReplayStore {
  private readonly status: ReplayReservation["status"];
  constructor(status: ReplayReservation["status"] = "RESERVED") { this.status = status; }
  reserve(): ReplayReservation {
    return this.status === "IDEMPOTENT"
      ? {status: this.status, cachedReceipt: load("valid-admission-receipt.json")}
      : {status: this.status};
  }
}

async function decide(
  envelope = load("valid-admission-envelope.json"),
  bundle = load("valid-trust-bundle.json"),
  overrides: Partial<{organizationId: string; now: string; store: Store; observed: Readonly<Record<string, number>>}> = {},
) {
  return verifyAdmission(envelope, bundle, {
    expectedOrganizationId: overrides.organizationId ?? "acme.example",
    idempotencyKeyDigest: `sha256:${"6".repeat(64)}`,
    limits,
    observed: overrides.observed ?? observed,
    replayStore: overrides.store ?? new Store(),
    now: overrides.now ?? "2030-02-01T00:00:01Z",
  });
}

test("TypeScript matches every CON-007 signed byte and digest", async () => {
  const vectors = load("interoperability-vectors.json") as {signedDocuments: Array<Record<string, string>>};
  for (const vector of vectors.signedDocuments) {
    const document = load(vector.fixture);
    const payload = document.payload as Record<string, unknown>;
    const encoded = Buffer.from(canonicalJson(payload)).toString("base64url");
    assert.equal(encoded, vector.canonicalPayloadBase64url, vector.kind);
    assert.equal(await sha256Digest(signedMessage(document.kind as "RuntimeTrustBundle", payload)), vector.signedMessageDigest, vector.kind);
  }
});

test("valid bootstrap, admission, and receipt pass with platform Web Crypto", async () => {
  const bundle = load("valid-trust-bundle.json");
  const pinned = await sha256Digest(canonicalJson(bundle));
  assert.equal((await verifyBootstrapBundle(bundle, pinned, "acme.example", "2030-02-01T00:00:01Z")).admitted, true);
  assert.equal((await decide()).admitted, true);
  assert.equal((await verifyReceipt(load("valid-admission-receipt.json"), bundle, "acme.example", "2030-02-01T00:00:01Z")).admitted, true);
});

test("rotation and replay helpers bind predecessor, tenant, nonce, and idempotency", async () => {
  const predecessor = load("valid-trust-bundle.json");
  const candidate = clone(predecessor);
  const payload = candidate.payload as Record<string, unknown>;
  payload.bundleVersion = 2;
  payload.previousBundleDigest = `sha256:${"0".repeat(64)}`;
  assert.equal((await verifyRotatedBundle(candidate, predecessor, "acme.example", "2030-02-01T00:00:01Z")).reasonCode, "DIGEST_MISMATCH");
  const digests = await replayDigests("acme.example", "AAAAAAAAAAAAAAAAAAAAAA", "local-idempotency-key-001");
  assert.match(digests.idempotencyKeyDigest, /^sha256:[0-9a-f]{64}$/);
  assert.match(digests.nonceDigest, /^sha256:[0-9a-f]{64}$/);
  assert.match(digests.replayKeyDigest, /^sha256:[0-9a-f]{64}$/);
  assert.doesNotMatch(JSON.stringify(digests), /local-idempotency-key-001/);
});

test("closed malformed, digest, signature, and signer reasons preserve precedence", async () => {
  const malformed = load("valid-admission-envelope.json");
  (malformed.payload as Record<string, unknown>).unknown = true;
  assert.equal((await decide(malformed)).reasonCode, "MALFORMED");
  const mismatch = load("valid-admission-envelope.json");
  (mismatch.payload as Record<string, unknown>).requestDigest = `sha256:${"1".repeat(64)}`;
  assert.equal((await decide(mismatch)).reasonCode, "DIGEST_MISMATCH");
  const forged = load("valid-admission-envelope.json");
  const signature = forged.signature as Record<string, string>;
  signature.value = `${signature.value[0] === "A" ? "B" : "A"}${signature.value.slice(1)}`;
  assert.equal((await decide(forged)).reasonCode, "SIGNATURE_INVALID");
  const unknown = load("valid-admission-envelope.json");
  (unknown.signature as Record<string, unknown>).keyId = "test.unknown-01";
  assert.equal((await decide(unknown)).reasonCode, "SIGNER_UNKNOWN");
});

test("key, tenant, time, replay, idempotency, and budget denials are distinct", async () => {
  const pending = load("valid-trust-bundle.json");
  (((pending.payload as Record<string, unknown>).keys as Array<Record<string, unknown>>)[0]!).state = "PENDING";
  assert.equal((await decide(undefined, pending)).reasonCode, "SIGNER_NOT_ACTIVE");
  const revoked = load("valid-trust-bundle.json");
  Object.assign((((revoked.payload as Record<string, unknown>).keys as Array<Record<string, unknown>>)[0]!), {state: "REVOKED", revokedAt: "2030-01-15T00:00:00Z", revocationReason: "KEY_COMPROMISE"});
  assert.equal((await decide(undefined, revoked)).reasonCode, "SIGNER_REVOKED");
  const purpose = load("valid-trust-bundle.json");
  (((purpose.payload as Record<string, unknown>).keys as Array<Record<string, unknown>>)[0]!).purposes = ["RUNTIME_RECEIPT"];
  assert.equal((await decide(undefined, purpose)).reasonCode, "KEY_PURPOSE_MISMATCH");
  assert.equal((await decide(undefined, undefined, {organizationId: "other.example"})).reasonCode, "TENANT_MISMATCH");
  assert.equal((await decide(undefined, undefined, {now: "2030-01-31T23:59:59Z"})).reasonCode, "ENVELOPE_NOT_YET_VALID");
  assert.equal((await decide(undefined, undefined, {now: "2030-02-01T00:05:00Z"})).reasonCode, "ENVELOPE_EXPIRED");
  assert.equal((await decide(undefined, undefined, {store: new Store("REPLAY_DETECTED")})).reasonCode, "REPLAY_DETECTED");
  assert.equal((await decide(undefined, undefined, {store: new Store("IDEMPOTENCY_CONFLICT")})).reasonCode, "IDEMPOTENCY_CONFLICT");
  const over = {...observed, modelTokens: 4097};
  assert.equal((await decide(undefined, undefined, {observed: over})).reasonCode, "BUDGET_EXCEEDED");
});

test("strict JSON parsing rejects duplicates and signed floats", () => {
  assert.throws(() => parseJsonStrict('{"a":1,"a":2}'), /duplicate/);
  assert.throws(() => canonicalJson(parseJsonStrict('{"a":1.5}')), /safe integer/);
});
