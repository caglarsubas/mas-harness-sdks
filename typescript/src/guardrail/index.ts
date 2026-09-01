/** Public SDK-006 local guardrail types and runtime. */

export type GuardrailStage = "INPUT" | "OUTPUT" | "RUNTIME" | "STREAMING";
export type FailMode = "FAIL_CLOSED" | "FAIL_OPEN";
export type DetectorAction = "ALLOW" | "DENY" | "REDACT" | "QUARANTINE";
export type GuardrailOutcome =
  | DetectorAction
  | "ERROR_FAIL_CLOSED"
  | "ERROR_FAIL_OPEN";
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

export {
  API_VERSION,
  DETECTOR_ACTIONS,
  FAIL_MODES,
  GUARDRAIL_OUTCOMES,
  GUARDRAIL_STAGES,
  MAXIMUM_CONTENT_BYTES,
  PROFILE_KIND,
  REDACTION_TOKEN,
  GuardrailClient,
  GuardrailContractError,
  GuardrailStream,
  canonicalGuardrailResult,
} from "./runtime.js";
