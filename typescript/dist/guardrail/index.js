/** Deterministic SDK-006 local guardrail runtime with no transport. */

export const API_VERSION = "harness.planeon.ai/v1alpha1";
export const PROFILE_KIND = "GuardrailProfile";
export const REDACTION_TOKEN = "[REDACTED]";
export const MAXIMUM_CONTENT_BYTES = 1048576;
export const GUARDRAIL_STAGES = Object.freeze(["INPUT", "OUTPUT", "RUNTIME", "STREAMING"]);
export const FAIL_MODES = Object.freeze(["FAIL_CLOSED", "FAIL_OPEN"]);
export const DETECTOR_ACTIONS = Object.freeze(["ALLOW", "DENY", "REDACT", "QUARANTINE"]);
export const GUARDRAIL_OUTCOMES = Object.freeze([
  "ALLOW",
  "DENY",
  "REDACT",
  "QUARANTINE",
  "ERROR_FAIL_CLOSED",
  "ERROR_FAIL_OPEN",
]);

const STABLE_ID = /^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)+$/;
const SEMVER = /^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$/;
const REASON_CODE = /^[A-Z][A-Z0-9_]{0,63}$/;
const ERROR_MESSAGES = Object.freeze({
  INVALID_GUARDRAIL_PROFILE: "guardrail profile is invalid",
  INVALID_GUARDRAIL_REQUEST: "guardrail request is invalid",
  UNKNOWN_DETECTOR: "guardrail detector registration is incomplete",
  INVALID_DETECTOR_RESULT: "guardrail detector result is invalid",
  STREAM_TERMINATED: "guardrail stream is terminated",
  STREAM_FINISHED: "guardrail stream is finished",
});

export class GuardrailContractError extends Error {
  constructor(code) {
    if (typeof code !== "string" || !Object.hasOwn(ERROR_MESSAGES, code)) {
      throw new Error("unknown guardrail error code");
    }
    const message = ERROR_MESSAGES[code];
    super(message);
    this.name = "GuardrailContractError";
    this.code = code;
  }
}

function fail(code) {
  throw new GuardrailContractError(code);
}

function plainObject(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function stableId(value) {
  return typeof value === "string" && value.length <= 128 && STABLE_ID.test(value);
}

function exactFields(value, fields) {
  if (!plainObject(value)) return false;
  const actual = Object.keys(value).sort();
  const expected = [...fields].sort();
  return actual.length === expected.length && actual.every((item, index) => item === expected[index]);
}

function validateProfile(value) {
  const fields = [
    "apiVersion",
    "kind",
    "profileId",
    "version",
    "stage",
    "failMode",
    "maximumContentBytes",
    "detectorIds",
  ];
  if (!exactFields(value, fields)) fail("INVALID_GUARDRAIL_PROFILE");
  if (
    value.apiVersion !== API_VERSION
    || value.kind !== PROFILE_KIND
    || !stableId(value.profileId)
    || typeof value.version !== "string"
    || !SEMVER.test(value.version)
    || !GUARDRAIL_STAGES.includes(value.stage)
    || !FAIL_MODES.includes(value.failMode)
    || !Number.isSafeInteger(value.maximumContentBytes)
    || value.maximumContentBytes < 1
    || value.maximumContentBytes > MAXIMUM_CONTENT_BYTES
    || !Array.isArray(value.detectorIds)
    || value.detectorIds.length < 1
    || value.detectorIds.length > 64
    || value.detectorIds.some((item) => !stableId(item))
    || new Set(value.detectorIds).size !== value.detectorIds.length
  ) {
    fail("INVALID_GUARDRAIL_PROFILE");
  }
  return Object.freeze({
    apiVersion: value.apiVersion,
    kind: value.kind,
    profileId: value.profileId,
    version: value.version,
    stage: value.stage,
    failMode: value.failMode,
    maximumContentBytes: value.maximumContentBytes,
    detectorIds: Object.freeze([...value.detectorIds]),
  });
}

function hasLoneSurrogate(value) {
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index);
    if (code >= 0xd800 && code <= 0xdbff) {
      const next = value.charCodeAt(index + 1);
      if (!(next >= 0xdc00 && next <= 0xdfff)) return true;
      index += 1;
    } else if (code >= 0xdc00 && code <= 0xdfff) {
      return true;
    }
  }
  return false;
}

function normalizeFinding(value, detectorId, scalarLength) {
  if (
    !exactFields(value, ["detectorId", "action", "reasonCode", "redactionRanges"])
    || value.detectorId !== detectorId
    || !stableId(value.detectorId)
    || !DETECTOR_ACTIONS.includes(value.action)
    || typeof value.reasonCode !== "string"
    || !REASON_CODE.test(value.reasonCode)
    || !Array.isArray(value.redactionRanges)
  ) {
    fail("INVALID_DETECTOR_RESULT");
  }
  const ranges = [];
  let previousEnd = -1;
  for (const item of value.redactionRanges) {
    if (
      !exactFields(item, ["start", "end"])
      || !Number.isSafeInteger(item.start)
      || !Number.isSafeInteger(item.end)
      || item.start < 0
      || item.end <= item.start
      || item.end > scalarLength
      || item.start < previousEnd
    ) {
      fail("INVALID_DETECTOR_RESULT");
    }
    ranges.push(Object.freeze({ start: item.start, end: item.end }));
    previousEnd = item.end;
  }
  if ((value.action === "REDACT" && ranges.length === 0) || (value.action !== "REDACT" && ranges.length !== 0)) {
    fail("INVALID_DETECTOR_RESULT");
  }
  return Object.freeze({
    detectorId: value.detectorId,
    action: value.action,
    reasonCode: value.reasonCode,
    redactionRanges: Object.freeze(ranges),
  });
}

function mergeRanges(findings) {
  const candidates = findings
    .filter((finding) => finding.action === "REDACT")
    .flatMap((finding) => finding.redactionRanges)
    .map((item) => ({ start: item.start, end: item.end }))
    .sort((left, right) => left.start - right.start || left.end - right.end);
  const merged = [];
  for (const item of candidates) {
    const previous = merged.at(-1);
    if (previous === undefined || item.start > previous.end) {
      merged.push(item);
    } else {
      previous.end = Math.max(previous.end, item.end);
    }
  }
  return merged;
}

function redact(content, findings) {
  const scalars = Array.from(content);
  const output = [];
  let cursor = 0;
  for (const range of mergeRanges(findings)) {
    output.push(...scalars.slice(cursor, range.start), REDACTION_TOKEN);
    cursor = range.end;
  }
  output.push(...scalars.slice(cursor));
  return output.join("");
}

function freezeResult(profile, outcome, reasonCode, findings = [], failed = [], redactedContent = null) {
  return Object.freeze({
    profileId: profile.profileId,
    profileVersion: profile.version,
    stage: profile.stage,
    outcome,
    reasonCode,
    detectorFindings: Object.freeze([...findings]),
    failedDetectorIds: Object.freeze([...failed]),
    degraded: failed.length > 0,
    redactedContent,
  });
}

function canonicalValue(value) {
  if (value === null || typeof value === "string" || typeof value === "boolean") return value;
  if (typeof value === "number" && Number.isSafeInteger(value)) return value;
  if (Array.isArray(value)) return value.map(canonicalValue);
  if (plainObject(value)) {
    return Object.fromEntries(
      Object.entries(value)
        .sort(([left], [right]) => (left < right ? -1 : left > right ? 1 : 0))
        .map(([key, item]) => [key, canonicalValue(item)]),
    );
  }
  throw new Error("guardrail result is not canonical JSON");
}

export function canonicalGuardrailResult(result) {
  return JSON.stringify(canonicalValue(result));
}

export class GuardrailClient {
  #detectors;
  #profile;

  constructor(profile, detectors) {
    this.#profile = validateProfile(profile);
    if (!Array.isArray(detectors)) fail("UNKNOWN_DETECTOR");
    const registered = new Map();
    for (const detector of detectors) {
      let detectorId;
      let evaluate;
      try {
        detectorId = detector?.detectorId;
        evaluate = detector?.evaluate;
      } catch {
        fail("UNKNOWN_DETECTOR");
      }
      if (
        !stableId(detectorId)
        || registered.has(detectorId)
        || typeof evaluate !== "function"
        || evaluate.constructor?.name === "AsyncFunction"
      ) {
        fail("UNKNOWN_DETECTOR");
      }
      registered.set(detectorId, detector);
    }
    if (
      registered.size !== this.#profile.detectorIds.length
      || this.#profile.detectorIds.some((detectorId) => !registered.has(detectorId))
    ) {
      fail("UNKNOWN_DETECTOR");
    }
    this.#detectors = registered;
  }

  get profile() {
    return this.#profile;
  }

  evaluate(content) {
    if (typeof content !== "string" || hasLoneSurrogate(content)) {
      fail("INVALID_GUARDRAIL_REQUEST");
    }
    if (new TextEncoder().encode(content).length > this.#profile.maximumContentBytes) {
      return freezeResult(this.#profile, "DENY", "PAYLOAD_TOO_LARGE");
    }

    const request = Object.freeze({ stage: this.#profile.stage, content });
    const scalarLength = Array.from(content).length;
    const findings = [];
    const failed = [];
    for (const detectorId of this.#profile.detectorIds) {
      const detector = this.#detectors.get(detectorId);
      try {
        findings.push(normalizeFinding(detector.evaluate(request), detectorId, scalarLength));
      } catch {
        failed.push(detectorId);
        if (this.#profile.failMode === "FAIL_CLOSED") {
          return freezeResult(this.#profile, "ERROR_FAIL_CLOSED", "DETECTOR_FAILURE", findings, failed);
        }
      }
    }

    const precedence = [
      ["DENY", "DENY"],
      ["QUARANTINE", "QUARANTINE"],
      ["REDACT", "REDACT"],
    ];
    for (const [action, outcome] of precedence) {
      const winner = findings.find((item) => item.action === action);
      if (winner !== undefined) {
        return freezeResult(
          this.#profile,
          outcome,
          winner.reasonCode,
          findings,
          failed,
          outcome === "REDACT" ? redact(content, findings) : null,
        );
      }
    }
    if (failed.length > 0) {
      return freezeResult(
        this.#profile,
        "ERROR_FAIL_OPEN",
        "DETECTOR_FAILURE_FAIL_OPEN",
        findings,
        failed,
      );
    }
    return freezeResult(this.#profile, "ALLOW", findings[0].reasonCode, findings);
  }

  stream() {
    if (this.#profile.stage !== "STREAMING") fail("INVALID_GUARDRAIL_PROFILE");
    return new GuardrailStream(this);
  }
}

const TERMINAL_OUTCOMES = new Set(["DENY", "QUARANTINE", "ERROR_FAIL_CLOSED"]);

export class GuardrailStream {
  #buffer = "";
  #client;
  #finished = false;
  #lastResult = null;
  #terminal = false;

  constructor(client) {
    if (!(client instanceof GuardrailClient) || client.profile.stage !== "STREAMING") {
      fail("INVALID_GUARDRAIL_PROFILE");
    }
    this.#client = client;
  }

  #requireOpen() {
    if (this.#finished) fail("STREAM_FINISHED");
    if (this.#terminal) fail("STREAM_TERMINATED");
  }

  push(chunk) {
    this.#requireOpen();
    if (typeof chunk !== "string" || chunk.length === 0) fail("INVALID_GUARDRAIL_REQUEST");
    const candidate = this.#buffer + chunk;
    const result = this.#client.evaluate(candidate);
    this.#lastResult = result;
    if (TERMINAL_OUTCOMES.has(result.outcome)) {
      this.#buffer = "";
      this.#terminal = true;
    } else {
      this.#buffer = candidate;
    }
    return result;
  }

  finish() {
    this.#requireOpen();
    const result = this.#lastResult ?? this.#client.evaluate("");
    this.#buffer = "";
    this.#finished = true;
    return result;
  }
}
