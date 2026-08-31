/** Fail-closed CON-007 runtime admission using platform Web Crypto. */

export type DenialReason =
  | "MALFORMED" | "SIGNATURE_INVALID" | "SIGNER_UNKNOWN" | "SIGNER_NOT_ACTIVE"
  | "SIGNER_REVOKED" | "KEY_PURPOSE_MISMATCH" | "ENVELOPE_NOT_YET_VALID"
  | "ENVELOPE_EXPIRED" | "TENANT_MISMATCH" | "REPLAY_DETECTED"
  | "IDEMPOTENCY_CONFLICT" | "BUDGET_EXCEEDED" | "DIGEST_MISMATCH";

export interface ReplayReservation {
  readonly status: "RESERVED" | "IDEMPOTENT" | "IDEMPOTENCY_CONFLICT" | "REPLAY_DETECTED";
  readonly cachedReceipt?: Readonly<Record<string, unknown>>;
}

export interface AtomicReplayStore {
  reserve(record: Readonly<Record<string, unknown>>): Promise<ReplayReservation> | ReplayReservation;
}

export interface AdmissionDecision {
  readonly admitted: boolean;
  readonly reasonCode: DenialReason | null;
  readonly admissionDigest?: string;
  readonly replayRecord?: Readonly<Record<string, unknown>>;
  readonly budgetConsumption?: Readonly<Record<string, unknown>>;
  readonly cachedReceipt?: Readonly<Record<string, unknown>>;
}

export interface AdmissionOptions {
  readonly expectedOrganizationId: string;
  readonly idempotencyKeyDigest: string;
  readonly limits: Readonly<Record<string, number>>;
  readonly observed: Readonly<Record<string, number>>;
  readonly replayStore: AtomicReplayStore;
  readonly now: string;
  readonly subtle?: SubtleCrypto;
}

const DOMAINS = Object.freeze({
  RuntimeTrustBundle: "harness.planeon.ai/runtime-trust-bundle/v1alpha1",
  SignedAdmissionEnvelope: "harness.planeon.ai/runtime-admission/v1alpha1",
  RuntimeAdmissionReceipt: "harness.planeon.ai/runtime-admission-receipt/v1alpha1",
});
const SHA256 = /^sha256:[0-9a-f]{64}$/;
const STABLE_ID = /^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)+$/;
const TIMESTAMP = /^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$/;
const PURPOSES = Object.freeze(["RUNTIME_ADMISSION", "RUNTIME_RECEIPT", "TRUST_BUNDLE"]);
const DENIAL_REASONS = Object.freeze(["MALFORMED", "SIGNATURE_INVALID", "SIGNER_UNKNOWN", "SIGNER_NOT_ACTIVE", "SIGNER_REVOKED", "KEY_PURPOSE_MISMATCH", "ENVELOPE_NOT_YET_VALID", "ENVELOPE_EXPIRED", "TENANT_MISMATCH", "REPLAY_DETECTED", "IDEMPOTENCY_CONFLICT", "BUDGET_EXCEEDED", "DIGEST_MISMATCH"]);
const textEncoder = new TextEncoder();

function fail(message: string): never { throw new Error(message); }

function canonicalValue(value: unknown, path = "$", seen = new Set<object>()): unknown {
  if (value === null || typeof value === "boolean") return value;
  if (typeof value === "string") {
    if (!/^[\x00-\x7f]*$/.test(value)) fail(`signed JSON string is not ASCII: ${path}`);
    return value;
  }
  if (typeof value === "number") {
    if (!Number.isSafeInteger(value) || Object.is(value, -0)) fail(`signed JSON number is not a safe integer: ${path}`);
    return value;
  }
  if (Array.isArray(value)) {
    if (seen.has(value)) fail(`signed JSON contains a cycle: ${path}`);
    seen.add(value);
    const result = value.map((item, index) => canonicalValue(item, `${path}[${index}]`, seen));
    seen.delete(value);
    return result;
  }
  if (typeof value === "object") {
    const prototype = Object.getPrototypeOf(value);
    if (prototype !== Object.prototype && prototype !== null) fail(`signed JSON object has a non-JSON prototype: ${path}`);
    if (seen.has(value)) fail(`signed JSON contains a cycle: ${path}`);
    seen.add(value);
    const record = value as Readonly<Record<string, unknown>>;
    const result: Record<string, unknown> = {};
    for (const key of Object.keys(record).sort()) {
      if (!/^[\x00-\x7f]*$/.test(key)) fail(`signed JSON property is not ASCII: ${path}`);
      result[key] = canonicalValue(record[key], `${path}.${key}`, seen);
    }
    seen.delete(value);
    return result;
  }
  return fail(`unsupported signed JSON value: ${path}`);
}

export function canonicalJson(value: unknown): string {
  return JSON.stringify(canonicalValue(value));
}

function scanJson(text: string): void {
  let offset = 0;
  const whitespace = (): void => { while (/\s/.test(text[offset] ?? "")) offset += 1; };
  const stringToken = (): string => {
    if (text[offset] !== '"') fail("JSON string expected");
    const start = offset;
    offset += 1;
    while (offset < text.length) {
      if (text[offset] === "\\") { offset += 2; continue; }
      if (text[offset] === '"') {
        offset += 1;
        return JSON.parse(text.slice(start, offset)) as string;
      }
      if ((text.charCodeAt(offset) || 0) < 0x20) fail("control character in JSON string");
      offset += 1;
    }
    return fail("unterminated JSON string");
  };
  const value = (): void => {
    whitespace();
    const token = text[offset];
    if (token === '"') { stringToken(); return; }
    if (token === "{") {
      offset += 1; whitespace();
      const keys = new Set<string>();
      if (text[offset] === "}") { offset += 1; return; }
      while (true) {
        whitespace(); const key = stringToken();
        if (keys.has(key)) fail(`duplicate JSON property: ${key}`);
        keys.add(key); whitespace();
        if (text[offset] !== ":") fail("JSON object colon expected");
        offset += 1; value(); whitespace();
        if (text[offset] === "}") { offset += 1; return; }
        if (text[offset] !== ",") fail("JSON object comma expected");
        offset += 1;
      }
    }
    if (token === "[") {
      offset += 1; whitespace();
      if (text[offset] === "]") { offset += 1; return; }
      while (true) {
        value(); whitespace();
        if (text[offset] === "]") { offset += 1; return; }
        if (text[offset] !== ",") fail("JSON array comma expected");
        offset += 1;
      }
    }
    const match = /^(?:true|false|null|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)/.exec(text.slice(offset));
    if (match === null) fail("invalid JSON token");
    offset += match[0].length;
  };
  value(); whitespace();
  if (offset !== text.length) fail("trailing JSON input");
}

export function parseJsonStrict(text: string): unknown {
  if (typeof text !== "string") fail("signed JSON input must be text");
  scanJson(text);
  return canonicalValue(JSON.parse(text) as unknown);
}

function bytesToBase64url(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
}

function base64urlBytes(value: unknown, size: number, field: string): Uint8Array {
  if (typeof value !== "string" || value.includes("=") || !/^[A-Za-z0-9_-]+$/.test(value)) fail(`${field} is not unpadded base64url`);
  let binary: string;
  try { binary = atob(value.replaceAll("-", "+").replaceAll("_", "/") + "=".repeat((4 - value.length % 4) % 4)); }
  catch { return fail(`${field} is not unpadded base64url`); }
  const result = Uint8Array.from(binary, (character) => character.charCodeAt(0));
  if (result.length !== size) fail(`${field} must decode to ${size} bytes`);
  return result;
}

export async function sha256Digest(value: Uint8Array | string, subtle = globalThis.crypto?.subtle): Promise<string> {
  if (subtle === undefined) fail("platform Web Crypto is unavailable");
  const bytes = typeof value === "string" ? textEncoder.encode(value) : value;
  const digest = new Uint8Array(await subtle.digest("SHA-256", bytes));
  return `sha256:${Array.from(digest, (item) => item.toString(16).padStart(2, "0")).join("")}`;
}

export async function replayDigests(organizationId: string, nonce: string, rawIdempotencyKey: string, subtle = globalThis.crypto?.subtle): Promise<Readonly<{idempotencyKeyDigest: string; nonceDigest: string; replayKeyDigest: string}>> {
  if (typeof rawIdempotencyKey !== "string" || rawIdempotencyKey.length < 16 || rawIdempotencyKey.length > 128) fail("raw idempotency key must contain 16-128 characters");
  const idempotencyKeyDigest = await sha256Digest(rawIdempotencyKey, subtle);
  const nonceDigest = await sha256Digest(base64urlBytes(nonce, 16, "nonce"), subtle);
  const replayKeyDigest = await sha256Digest(canonicalJson({nonceDigest, organizationId}), subtle);
  return Object.freeze({idempotencyKeyDigest, nonceDigest, replayKeyDigest});
}

export function signedMessage(kind: keyof typeof DOMAINS, payload: Readonly<Record<string, unknown>>): Uint8Array {
  const domain = DOMAINS[kind];
  if (domain === undefined) fail(`unsupported signed document kind: ${kind}`);
  const left = textEncoder.encode(`${domain}\0`);
  const right = textEncoder.encode(canonicalJson(payload));
  const result = new Uint8Array(left.length + right.length);
  result.set(left); result.set(right, left.length);
  return result;
}

function object(value: unknown, fields: readonly string[], context: string): Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) fail(`${context} must be an object`);
  const record = value as Record<string, unknown>;
  const keys = Object.keys(record).sort();
  if (keys.length !== fields.length || keys.some((key, index) => key !== [...fields].sort()[index])) fail(`${context} fields are closed`);
  return record;
}

function timestamp(value: unknown, context: string): number {
  if (typeof value !== "string" || !TIMESTAMP.test(value)) fail(`${context} must be a whole-second UTC timestamp`);
  const result = Date.parse(value);
  if (!Number.isFinite(result) || new Date(result).toISOString().replace(".000Z", "Z") !== value) fail(`${context} is not a calendar timestamp`);
  return result;
}

function validateSignature(value: unknown, purpose: string): Record<string, unknown> {
  const signature = object(value, ["profile", "algorithm", "purpose", "keyId", "signedMessageDigest", "value"], "signature");
  if (signature.profile !== "RFC8785_JCS_ED25519_V1" || signature.algorithm !== "ED25519" || signature.purpose !== purpose) fail("signature profile is invalid");
  if (typeof signature.keyId !== "string" || !STABLE_ID.test(signature.keyId)) fail("signature.keyId is invalid");
  if (typeof signature.signedMessageDigest !== "string" || !SHA256.test(signature.signedMessageDigest)) fail("signature digest is invalid");
  base64urlBytes(signature.value, 64, "signature.value");
  return signature;
}

function validateSigned(value: unknown, kind: keyof typeof DOMAINS, purpose: string): Record<string, unknown> {
  canonicalValue(value);
  const document = object(value, ["apiVersion", "kind", "metadata", "payload", "signature"], kind);
  if (document.apiVersion !== "harness.planeon.ai/v1alpha1" || document.kind !== kind) fail(`${kind} identity is invalid`);
  const metadata = object(document.metadata, ["id", "version"], "metadata");
  if (typeof metadata.id !== "string" || !STABLE_ID.test(metadata.id) || typeof metadata.version !== "string" || !/^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$/.test(metadata.version)) fail("metadata is invalid");
  object(document.payload, Object.keys(document.payload as Record<string, unknown>), `${kind}.payload`);
  validateSignature(document.signature, purpose);
  return document;
}

function validateTrustBundle(value: unknown): Record<string, unknown> {
  const document = validateSigned(value, "RuntimeTrustBundle", "TRUST_BUNDLE");
  const payload = object(document.payload, ["organizationId", "bundleVersion", "issuedAt", "validFrom", "validUntil", "previousBundleDigest", "keys"], "trust.payload");
  if (typeof payload.organizationId !== "string" || !STABLE_ID.test(payload.organizationId)) fail("trust organizationId is invalid");
  if (!Number.isInteger(payload.bundleVersion) || (payload.bundleVersion as number) < 1) fail("trust bundleVersion is invalid");
  const issued = timestamp(payload.issuedAt, "trust.issuedAt"); const from = timestamp(payload.validFrom, "trust.validFrom"); const until = timestamp(payload.validUntil, "trust.validUntil");
  if (!(issued <= from && from < until)) fail("trust timestamps are not ordered");
  if (payload.previousBundleDigest !== null && (typeof payload.previousBundleDigest !== "string" || !SHA256.test(payload.previousBundleDigest))) fail("previousBundleDigest is invalid");
  if (!Array.isArray(payload.keys) || payload.keys.length < 1 || payload.keys.length > 128) fail("trust keys are invalid");
  const seen = new Set<string>();
  for (const rawKey of payload.keys) {
    const key = object(rawKey, ["keyId", "algorithm", "publicKey", "purposes", "state", "notBefore", "notAfter", "revokedAt", "revocationReason"], "trust.key");
    if (typeof key.keyId !== "string" || key.keyId.length > 128 || !STABLE_ID.test(key.keyId) || seen.has(key.keyId)) fail("trust keyId is invalid");
    seen.add(key.keyId);
    if (key.algorithm !== "ED25519") fail("trust algorithm is invalid");
    base64urlBytes(key.publicKey, 32, "trust.publicKey");
    if (!Array.isArray(key.purposes) || key.purposes.length < 1 || new Set(key.purposes).size !== key.purposes.length || key.purposes.some((purpose) => !PURPOSES.includes(purpose as string))) fail("trust purposes are invalid");
    if (!["PENDING", "ACTIVE", "RETIRED", "REVOKED"].includes(key.state as string)) fail("trust state is invalid");
    if (timestamp(key.notBefore, "trust.notBefore") >= timestamp(key.notAfter, "trust.notAfter")) fail("trust key timestamps are not ordered");
    if (key.state === "REVOKED") {
      timestamp(key.revokedAt, "trust.revokedAt");
      if (!["KEY_COMPROMISE", "AUTHORITY_WITHDRAWN", "SUPERSEDED", "POLICY_VIOLATION"].includes(key.revocationReason as string)) fail("trust revocation is invalid");
    } else if (key.revokedAt !== null || key.revocationReason !== null) fail("non-revoked key has revocation metadata");
  }
  return document;
}

function validateEnvelope(value: unknown): Record<string, unknown> {
  const document = validateSigned(value, "SignedAdmissionEnvelope", "RUNTIME_ADMISSION");
  const payload = object(document.payload, ["organizationId", "admissionId", "subjectDigest", "releaseDigest", "policyDigest", "budgetDigest", "requestDigest", "operation", "issuedAt", "notBefore", "expiresAt", "nonce", "idempotencyKeyDigest"], "admission.payload");
  if (typeof payload.organizationId !== "string" || !STABLE_ID.test(payload.organizationId) || typeof payload.admissionId !== "string" || !STABLE_ID.test(payload.admissionId)) fail("admission identity is invalid");
  for (const field of ["subjectDigest", "releaseDigest", "policyDigest", "budgetDigest", "requestDigest", "idempotencyKeyDigest"]) if (typeof payload[field] !== "string" || !SHA256.test(payload[field] as string)) fail(`admission ${field} is invalid`);
  if (!["MODEL_INFERENCE", "AGENT_RUN", "TOOL_EXECUTION", "WORKFLOW_RESUME"].includes(payload.operation as string)) fail("admission operation is invalid");
  const issued = timestamp(payload.issuedAt, "admission.issuedAt"); const from = timestamp(payload.notBefore, "admission.notBefore"); const until = timestamp(payload.expiresAt, "admission.expiresAt");
  if (!(issued <= from && from < until)) fail("admission timestamps are not ordered");
  base64urlBytes(payload.nonce, 16, "admission.nonce");
  return document;
}

async function verifySignature(document: Record<string, unknown>, publicKey: unknown, subtle: SubtleCrypto): Promise<{digest: boolean; signature: boolean}> {
  const kind = document.kind as keyof typeof DOMAINS;
  const message = signedMessage(kind, document.payload as Record<string, unknown>);
  const signature = document.signature as Record<string, unknown>;
  if (await sha256Digest(message, subtle) !== signature.signedMessageDigest) return {digest: false, signature: false};
  const key = await subtle.importKey("raw", base64urlBytes(publicKey, 32, "publicKey"), {name: "Ed25519"}, false, ["verify"]);
  const valid = await subtle.verify({name: "Ed25519"}, key, base64urlBytes(signature.value, 64, "signature.value"), message);
  return {digest: true, signature: valid};
}

function selectKey(bundle: Record<string, unknown>, keyId: unknown, purpose: string, now: number): {key?: Record<string, unknown>; reason?: DenialReason} {
  const payload = bundle.payload as Record<string, unknown>;
  const key = (payload.keys as Record<string, unknown>[]).find((item) => item.keyId === keyId);
  if (key === undefined) return {reason: "SIGNER_UNKNOWN"};
  if (key.state === "REVOKED") return {reason: "SIGNER_REVOKED"};
  if (key.state !== "ACTIVE") return {reason: "SIGNER_NOT_ACTIVE"};
  if (!(key.purposes as unknown[]).includes(purpose)) return {reason: "KEY_PURPOSE_MISMATCH"};
  if (!(timestamp(key.notBefore, "key.notBefore") <= now && now < timestamp(key.notAfter, "key.notAfter"))) return {reason: "SIGNER_NOT_ACTIVE"};
  return {key};
}

const BUDGET = Object.freeze([
  ["maxConcurrentTasks", "concurrentTasks", "CONCURRENT_TASKS", 1, 1024, 0, 1025],
  ["maxTaskSeconds", "taskSeconds", "TASK_SECONDS", 1, 86400, 0, 86401],
  ["maxRetries", "retries", "RETRIES", 0, 100, 0, 101],
  ["maxToolCalls", "toolCalls", "TOOL_CALLS", 0, 10000, 0, 10001],
  ["maxModelTokens", "modelTokens", "MODEL_TOKENS", 0, 10000000, 0, 10000001],
] as const);

export function evaluateBudget(organizationId: string, budgetDigest: string, admissionDigest: string, limits: Readonly<Record<string, number>>, observed: Readonly<Record<string, number>>, recordedAt: string, recordId: string): Readonly<Record<string, unknown>> {
  if (!SHA256.test(budgetDigest) || !SHA256.test(admissionDigest)) fail("budget digests are invalid");
  if (Object.keys(limits).sort().join() !== BUDGET.map((item) => item[0]).sort().join() || Object.keys(observed).sort().join() !== BUDGET.map((item) => item[1]).sort().join()) fail("budget dimensions are incomplete");
  timestamp(recordedAt, "budget.recordedAt");
  const exceeded: string[] = [];
  for (const [limit, current, dimension, limitMin, limitMax, currentMin, currentMax] of BUDGET) {
    if (!Number.isSafeInteger(limits[limit]) || !Number.isSafeInteger(observed[current]) || limits[limit]! < limitMin || limits[limit]! > limitMax || observed[current]! < currentMin || observed[current]! > currentMax) fail("budget value is invalid");
    if (observed[current]! > limits[limit]!) exceeded.push(dimension);
  }
  return Object.freeze({apiVersion: "harness.planeon.ai/v1alpha1", kind: "BudgetConsumption", metadata: {id: recordId, version: "1.0.0"}, spec: {organizationId, budgetDigest, admissionDigest, limits: {...limits}, observed: {...observed}, decision: exceeded.length === 0 ? "WITHIN_BUDGET" : "OVER_BUDGET", exceededDimensions: exceeded, recordedAt}});
}

async function documentDigest(document: Record<string, unknown>, subtle: SubtleCrypto): Promise<string> { return sha256Digest(canonicalJson(document), subtle); }

export async function verifyAdmission(rawEnvelope: unknown, rawBundle: unknown, options: AdmissionOptions): Promise<AdmissionDecision> {
  const deny = (reasonCode: DenialReason, admissionDigest?: string): AdmissionDecision => ({admitted: false, reasonCode, ...(admissionDigest === undefined ? {} : {admissionDigest})});
  const subtle = options.subtle ?? globalThis.crypto?.subtle;
  if (subtle === undefined) return deny("MALFORMED");
  let envelope: Record<string, unknown>; let bundle: Record<string, unknown>; let now: number;
  try { envelope = validateEnvelope(rawEnvelope); bundle = validateTrustBundle(rawBundle); now = timestamp(options.now, "now"); }
  catch { return deny("MALFORMED"); }
  const admissionDigest = await documentDigest(envelope, subtle);
  const signature = envelope.signature as Record<string, unknown>; const payload = envelope.payload as Record<string, unknown>;
  const message = signedMessage("SignedAdmissionEnvelope", payload);
  if (await sha256Digest(message, subtle) !== signature.signedMessageDigest) return deny("DIGEST_MISMATCH", admissionDigest);
  const bundlePayload = bundle.payload as Record<string, unknown>;
  if (payload.organizationId !== options.expectedOrganizationId || bundlePayload.organizationId !== options.expectedOrganizationId) return deny("TENANT_MISMATCH", admissionDigest);
  const selected = selectKey(bundle, signature.keyId, "RUNTIME_ADMISSION", now);
  if (selected.reason !== undefined || selected.key === undefined) return deny(selected.reason ?? "SIGNER_UNKNOWN", admissionDigest);
  try { if (!(await verifySignature(envelope, selected.key.publicKey, subtle)).signature) return deny("SIGNATURE_INVALID", admissionDigest); }
  catch { return deny("SIGNATURE_INVALID", admissionDigest); }
  if (now < timestamp(payload.notBefore, "admission.notBefore")) return deny("ENVELOPE_NOT_YET_VALID", admissionDigest);
  if (now >= timestamp(payload.expiresAt, "admission.expiresAt")) return deny("ENVELOPE_EXPIRED", admissionDigest);
  if (typeof options.idempotencyKeyDigest !== "string" || !SHA256.test(options.idempotencyKeyDigest)) return deny("MALFORMED", admissionDigest);
  const idempotencyKeyDigest = options.idempotencyKeyDigest;
  if (idempotencyKeyDigest !== payload.idempotencyKeyDigest) return deny("IDEMPOTENCY_CONFLICT", admissionDigest);
  const nonceDigest = await sha256Digest(base64urlBytes(payload.nonce, 16, "nonce"), subtle);
  const replayKeyDigest = await sha256Digest(canonicalJson({nonceDigest, organizationId: payload.organizationId}), subtle);
  const replayRecord = Object.freeze({apiVersion: "harness.planeon.ai/v1alpha1", kind: "ReplayRecord", metadata: {id: `${payload.admissionId as string}.replay`, version: "1.0.0"}, spec: {organizationId: payload.organizationId, replayKeyDigest, idempotencyKeyDigest, nonceDigest, admissionDigest, requestDigest: payload.requestDigest, state: "RESERVED", firstSeenAt: options.now, updatedAt: options.now, expiresAt: payload.expiresAt, receiptDigest: null}});
  let reservation: ReplayReservation;
  try { reservation = await options.replayStore.reserve(replayRecord); }
  catch { return deny("REPLAY_DETECTED", admissionDigest); }
  if (reservation.status === "IDEMPOTENT" && reservation.cachedReceipt !== undefined) return {admitted: true, reasonCode: null, admissionDigest, replayRecord, cachedReceipt: reservation.cachedReceipt};
  if (reservation.status === "IDEMPOTENCY_CONFLICT") return deny("IDEMPOTENCY_CONFLICT", admissionDigest);
  if (reservation.status !== "RESERVED") return deny("REPLAY_DETECTED", admissionDigest);
  let budget: Readonly<Record<string, unknown>>;
  try { budget = evaluateBudget(options.expectedOrganizationId, payload.budgetDigest as string, admissionDigest, options.limits, options.observed, options.now, `${payload.admissionId as string}.budget`); }
  catch { return deny("MALFORMED", admissionDigest); }
  if ((budget.spec as Record<string, unknown>).decision === "OVER_BUDGET") return {admitted: false, reasonCode: "BUDGET_EXCEEDED", admissionDigest, replayRecord, budgetConsumption: budget};
  return {admitted: true, reasonCode: null, admissionDigest, replayRecord, budgetConsumption: budget};
}

export async function verifyBootstrapBundle(rawBundle: unknown, pinnedDigest: string, expectedOrganizationId: string, nowText: string, subtle = globalThis.crypto?.subtle): Promise<AdmissionDecision> {
  if (subtle === undefined) return {admitted: false, reasonCode: "MALFORMED"};
  try {
    const bundle = validateTrustBundle(rawBundle); const digest = await documentDigest(bundle, subtle); const payload = bundle.payload as Record<string, unknown>; const signature = bundle.signature as Record<string, unknown>; const now = timestamp(nowText, "now");
    if (digest !== pinnedDigest) return {admitted: false, reasonCode: "DIGEST_MISMATCH"};
    if (payload.organizationId !== expectedOrganizationId) return {admitted: false, reasonCode: "TENANT_MISMATCH"};
    if (payload.bundleVersion !== 1 || payload.previousBundleDigest !== null) return {admitted: false, reasonCode: "MALFORMED"};
    if (!(timestamp(payload.validFrom, "trust.validFrom") <= now && now < timestamp(payload.validUntil, "trust.validUntil"))) return {admitted: false, reasonCode: "SIGNER_NOT_ACTIVE"};
    const selected = selectKey(bundle, signature.keyId, "TRUST_BUNDLE", now); if (selected.reason !== undefined || selected.key === undefined) return {admitted: false, reasonCode: selected.reason ?? "SIGNER_UNKNOWN"};
    const verified = await verifySignature(bundle, selected.key.publicKey, subtle); if (!verified.digest) return {admitted: false, reasonCode: "DIGEST_MISMATCH"}; if (!verified.signature) return {admitted: false, reasonCode: "SIGNATURE_INVALID"};
    return {admitted: true, reasonCode: null, admissionDigest: digest};
  } catch { return {admitted: false, reasonCode: "MALFORMED"}; }
}

export async function verifyRotatedBundle(rawCandidate: unknown, rawPredecessor: unknown, expectedOrganizationId: string, nowText: string, subtle = globalThis.crypto?.subtle): Promise<AdmissionDecision> {
  if (subtle === undefined) return {admitted: false, reasonCode: "MALFORMED"};
  try {
    const candidate = validateTrustBundle(rawCandidate); const predecessor = validateTrustBundle(rawPredecessor); const candidatePayload = candidate.payload as Record<string, unknown>; const predecessorPayload = predecessor.payload as Record<string, unknown>; const signature = candidate.signature as Record<string, unknown>; const now = timestamp(nowText, "now");
    if (candidatePayload.organizationId !== expectedOrganizationId || predecessorPayload.organizationId !== expectedOrganizationId) return {admitted: false, reasonCode: "TENANT_MISMATCH"};
    if (candidatePayload.bundleVersion !== (predecessorPayload.bundleVersion as number) + 1) return {admitted: false, reasonCode: "MALFORMED"};
    if (candidatePayload.previousBundleDigest !== await documentDigest(predecessor, subtle)) return {admitted: false, reasonCode: "DIGEST_MISMATCH"};
    const selected = selectKey(predecessor, signature.keyId, "TRUST_BUNDLE", now); if (selected.reason !== undefined || selected.key === undefined) return {admitted: false, reasonCode: selected.reason ?? "SIGNER_UNKNOWN"};
    const verified = await verifySignature(candidate, selected.key.publicKey, subtle); if (!verified.digest) return {admitted: false, reasonCode: "DIGEST_MISMATCH"}; if (!verified.signature) return {admitted: false, reasonCode: "SIGNATURE_INVALID"};
    return {admitted: true, reasonCode: null, admissionDigest: await documentDigest(candidate, subtle)};
  } catch { return {admitted: false, reasonCode: "MALFORMED"}; }
}

export async function verifyReceipt(rawReceipt: unknown, rawBundle: unknown, expectedOrganizationId: string, nowText: string, subtle = globalThis.crypto?.subtle): Promise<AdmissionDecision> {
  if (subtle === undefined) return {admitted: false, reasonCode: "MALFORMED"};
  try {
    const receipt = validateSigned(rawReceipt, "RuntimeAdmissionReceipt", "RUNTIME_RECEIPT"); const payload = object(receipt.payload, ["organizationId", "receiptId", "admissionDigest", "requestDigest", "trustBundleDigest", "decision", "reasonCode", "budgetConsumptionDigest", "replayRecordDigest", "decidedAt", "expiresAt"], "receipt.payload"); const bundle = validateTrustBundle(rawBundle); const bundlePayload = bundle.payload as Record<string, unknown>; const signature = receipt.signature as Record<string, unknown>; const now = timestamp(nowText, "now");
    if (payload.organizationId !== expectedOrganizationId || bundlePayload.organizationId !== expectedOrganizationId) return {admitted: false, reasonCode: "TENANT_MISMATCH"};
    for (const field of ["admissionDigest", "requestDigest", "trustBundleDigest"]) if (typeof payload[field] !== "string" || !SHA256.test(payload[field] as string)) return {admitted: false, reasonCode: "MALFORMED"};
    if (payload.decision !== "ADMIT" && payload.decision !== "DENY") return {admitted: false, reasonCode: "MALFORMED"};
    if (payload.decision === "ADMIT" ? payload.reasonCode !== null || typeof payload.budgetConsumptionDigest !== "string" || !SHA256.test(payload.budgetConsumptionDigest) || typeof payload.replayRecordDigest !== "string" || !SHA256.test(payload.replayRecordDigest) : typeof payload.reasonCode !== "string" || !DENIAL_REASONS.includes(payload.reasonCode)) return {admitted: false, reasonCode: "MALFORMED"};
    if (payload.decision === "DENY") for (const field of ["budgetConsumptionDigest", "replayRecordDigest"]) if (payload[field] !== null && (typeof payload[field] !== "string" || !SHA256.test(payload[field] as string))) return {admitted: false, reasonCode: "MALFORMED"};
    if (!(timestamp(payload.decidedAt, "receipt.decidedAt") < timestamp(payload.expiresAt, "receipt.expiresAt"))) return {admitted: false, reasonCode: "MALFORMED"};
    const selected = selectKey(bundle, signature.keyId, "RUNTIME_RECEIPT", now); if (selected.reason !== undefined || selected.key === undefined) return {admitted: false, reasonCode: selected.reason ?? "SIGNER_UNKNOWN"};
    const verified = await verifySignature(receipt, selected.key.publicKey, subtle); if (!verified.digest) return {admitted: false, reasonCode: "DIGEST_MISMATCH"}; if (!verified.signature) return {admitted: false, reasonCode: "SIGNATURE_INVALID"};
    if (now >= timestamp(payload.expiresAt, "receipt.expiresAt")) return {admitted: false, reasonCode: "ENVELOPE_EXPIRED"};
    return {admitted: true, reasonCode: null, admissionDigest: await documentDigest(receipt, subtle)};
  } catch { return {admitted: false, reasonCode: "MALFORMED"}; }
}
