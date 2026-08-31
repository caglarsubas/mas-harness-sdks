export type DenialReason = "MALFORMED" | "SIGNATURE_INVALID" | "SIGNER_UNKNOWN" | "SIGNER_NOT_ACTIVE" | "SIGNER_REVOKED" | "KEY_PURPOSE_MISMATCH" | "ENVELOPE_NOT_YET_VALID" | "ENVELOPE_EXPIRED" | "TENANT_MISMATCH" | "REPLAY_DETECTED" | "IDEMPOTENCY_CONFLICT" | "BUDGET_EXCEEDED" | "DIGEST_MISMATCH";
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
export declare function canonicalJson(value: unknown): string;
export declare function parseJsonStrict(text: string): unknown;
export declare function sha256Digest(value: Uint8Array | string, subtle?: SubtleCrypto): Promise<string>;
export declare function replayDigests(organizationId: string, nonce: string, rawIdempotencyKey: string, subtle?: SubtleCrypto): Promise<Readonly<{idempotencyKeyDigest: string; nonceDigest: string; replayKeyDigest: string}>>;
export declare function signedMessage(kind: "RuntimeTrustBundle" | "SignedAdmissionEnvelope" | "RuntimeAdmissionReceipt", payload: Readonly<Record<string, unknown>>): Uint8Array;
export declare function evaluateBudget(organizationId: string, budgetDigest: string, admissionDigest: string, limits: Readonly<Record<string, number>>, observed: Readonly<Record<string, number>>, recordedAt: string, recordId: string): Readonly<Record<string, unknown>>;
export declare function verifyAdmission(rawEnvelope: unknown, rawBundle: unknown, options: AdmissionOptions): Promise<AdmissionDecision>;
export declare function verifyBootstrapBundle(rawBundle: unknown, pinnedDigest: string, expectedOrganizationId: string, nowText: string, subtle?: SubtleCrypto): Promise<AdmissionDecision>;
export declare function verifyRotatedBundle(rawCandidate: unknown, rawPredecessor: unknown, expectedOrganizationId: string, nowText: string, subtle?: SubtleCrypto): Promise<AdmissionDecision>;
export declare function verifyReceipt(rawReceipt: unknown, rawBundle: unknown, expectedOrganizationId: string, nowText: string, subtle?: SubtleCrypto): Promise<AdmissionDecision>;
