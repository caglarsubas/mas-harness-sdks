export type GuardrailStage = "INPUT" | "OUTPUT" | "RUNTIME" | "STREAMING";
export type FailMode = "FAIL_CLOSED" | "FAIL_OPEN";
export type DetectorAction = "ALLOW" | "DENY" | "REDACT" | "QUARANTINE";
export type GuardrailOutcome = DetectorAction | "ERROR_FAIL_CLOSED" | "ERROR_FAIL_OPEN";
export type GuardrailErrorCode =
  | "INVALID_GUARDRAIL_PROFILE"
  | "INVALID_GUARDRAIL_REQUEST"
  | "UNKNOWN_DETECTOR"
  | "INVALID_DETECTOR_RESULT"
  | "STREAM_TERMINATED"
  | "STREAM_FINISHED";

export interface RedactionRange {
  readonly start: number;
  readonly end: number;
}

export interface GuardrailProfile {
  readonly apiVersion: "harness.planeon.ai/v1alpha1";
  readonly kind: "GuardrailProfile";
  readonly profileId: string;
  readonly version: string;
  readonly stage: GuardrailStage;
  readonly failMode: FailMode;
  readonly maximumContentBytes: number;
  readonly detectorIds: readonly string[];
}

export interface GuardrailRequest {
  readonly stage: GuardrailStage;
  readonly content: string;
}

export interface DetectorFinding {
  readonly detectorId: string;
  readonly action: DetectorAction;
  readonly reasonCode: string;
  readonly redactionRanges: readonly RedactionRange[];
}

export interface GuardrailResult {
  readonly profileId: string;
  readonly profileVersion: string;
  readonly stage: GuardrailStage;
  readonly outcome: GuardrailOutcome;
  readonly reasonCode: string;
  readonly detectorFindings: readonly DetectorFinding[];
  readonly failedDetectorIds: readonly string[];
  readonly degraded: boolean;
  readonly redactedContent: string | null;
}

export interface GuardrailDetector {
  readonly detectorId: string;
  evaluate(request: GuardrailRequest): DetectorFinding;
}

export declare const API_VERSION: "harness.planeon.ai/v1alpha1";
export declare const PROFILE_KIND: "GuardrailProfile";
export declare const REDACTION_TOKEN: "[REDACTED]";
export declare const MAXIMUM_CONTENT_BYTES: 1048576;
export declare const GUARDRAIL_STAGES: readonly GuardrailStage[];
export declare const FAIL_MODES: readonly FailMode[];
export declare const DETECTOR_ACTIONS: readonly DetectorAction[];
export declare const GUARDRAIL_OUTCOMES: readonly GuardrailOutcome[];

export declare class GuardrailContractError extends Error {
  readonly code: GuardrailErrorCode;
  constructor(code: GuardrailErrorCode);
}

export declare class GuardrailClient {
  constructor(profile: GuardrailProfile, detectors: readonly GuardrailDetector[]);
  get profile(): GuardrailProfile;
  evaluate(content: string): GuardrailResult;
  stream(): GuardrailStream;
}

export declare class GuardrailStream {
  constructor(client: GuardrailClient);
  push(chunk: string): GuardrailResult;
  finish(): GuardrailResult;
}

export declare function canonicalGuardrailResult(result: GuardrailResult): string;
