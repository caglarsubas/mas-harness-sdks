"""Deterministic, transport-neutral local guardrail evaluation."""

from __future__ import annotations

import inspect
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Protocol, runtime_checkable


API_VERSION = "harness.planeon.ai/v1alpha1"
PROFILE_KIND = "GuardrailProfile"
REDACTION_TOKEN = "[REDACTED]"
MAXIMUM_CONTENT_BYTES = 1_048_576

_STABLE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)+$")
_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_REASON_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_ERROR_MESSAGES = MappingProxyType(
    {
        "INVALID_GUARDRAIL_PROFILE": "guardrail profile is invalid",
        "INVALID_GUARDRAIL_REQUEST": "guardrail request is invalid",
        "UNKNOWN_DETECTOR": "guardrail detector registration is incomplete",
        "INVALID_DETECTOR_RESULT": "guardrail detector result is invalid",
        "STREAM_TERMINATED": "guardrail stream is terminated",
        "STREAM_FINISHED": "guardrail stream is finished",
    }
)


class GuardrailStage(str, Enum):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    RUNTIME = "RUNTIME"
    STREAMING = "STREAMING"


class FailMode(str, Enum):
    FAIL_CLOSED = "FAIL_CLOSED"
    FAIL_OPEN = "FAIL_OPEN"


class DetectorAction(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REDACT = "REDACT"
    QUARANTINE = "QUARANTINE"


class GuardrailOutcome(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REDACT = "REDACT"
    QUARANTINE = "QUARANTINE"
    ERROR_FAIL_CLOSED = "ERROR_FAIL_CLOSED"
    ERROR_FAIL_OPEN = "ERROR_FAIL_OPEN"


class GuardrailContractError(ValueError):
    """A closed, content-free public guardrail contract error."""

    def __init__(self, code: str) -> None:
        message = _ERROR_MESSAGES.get(code)
        if message is None:
            raise ValueError("unknown guardrail error code")
        self.code = code
        super().__init__(message)


def _invalid_profile() -> GuardrailContractError:
    return GuardrailContractError("INVALID_GUARDRAIL_PROFILE")


def _invalid_request() -> GuardrailContractError:
    return GuardrailContractError("INVALID_GUARDRAIL_REQUEST")


def _invalid_finding() -> GuardrailContractError:
    return GuardrailContractError("INVALID_DETECTOR_RESULT")


def _is_stable_id(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) <= 128
        and _STABLE_ID.fullmatch(value) is not None
    )


@dataclass(frozen=True, slots=True)
class RedactionRange:
    """A half-open range measured in Unicode scalar values."""

    start: int
    end: int

    def __post_init__(self) -> None:
        if (
            type(self.start) is not int
            or type(self.end) is not int
            or self.start < 0
            or self.end <= self.start
        ):
            raise _invalid_finding()

    def to_dict(self) -> dict[str, int]:
        return {"start": self.start, "end": self.end}


@dataclass(frozen=True, slots=True)
class GuardrailProfile:
    """One closed local detector and failure-mode policy."""

    api_version: str
    kind: str
    profile_id: str
    version: str
    stage: GuardrailStage
    fail_mode: FailMode
    maximum_content_bytes: int
    detector_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            self.api_version != API_VERSION
            or self.kind != PROFILE_KIND
            or not _is_stable_id(self.profile_id)
            or not isinstance(self.version, str)
            or _SEMVER.fullmatch(self.version) is None
            or not isinstance(self.stage, GuardrailStage)
            or not isinstance(self.fail_mode, FailMode)
            or type(self.maximum_content_bytes) is not int
            or not 1 <= self.maximum_content_bytes <= MAXIMUM_CONTENT_BYTES
            or not isinstance(self.detector_ids, tuple)
            or not 1 <= len(self.detector_ids) <= 64
            or any(not _is_stable_id(item) for item in self.detector_ids)
            or len(set(self.detector_ids)) != len(self.detector_ids)
        ):
            raise _invalid_profile()

    @classmethod
    def from_dict(cls, value: object) -> GuardrailProfile:
        if not isinstance(value, dict) or set(value) != {
            "apiVersion",
            "kind",
            "profileId",
            "version",
            "stage",
            "failMode",
            "maximumContentBytes",
            "detectorIds",
        }:
            raise _invalid_profile()
        detector_ids = value["detectorIds"]
        if not isinstance(detector_ids, list):
            raise _invalid_profile()
        if value["stage"] not in tuple(item.value for item in GuardrailStage) or value[
            "failMode"
        ] not in tuple(item.value for item in FailMode):
            raise _invalid_profile()
        stage = GuardrailStage(value["stage"])
        fail_mode = FailMode(value["failMode"])
        return cls(
            api_version=value["apiVersion"],
            kind=value["kind"],
            profile_id=value["profileId"],
            version=value["version"],
            stage=stage,
            fail_mode=fail_mode,
            maximum_content_bytes=value["maximumContentBytes"],
            detector_ids=tuple(detector_ids),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "apiVersion": self.api_version,
            "kind": self.kind,
            "profileId": self.profile_id,
            "version": self.version,
            "stage": self.stage.value,
            "failMode": self.fail_mode.value,
            "maximumContentBytes": self.maximum_content_bytes,
            "detectorIds": list(self.detector_ids),
        }


@dataclass(frozen=True, slots=True)
class GuardrailRequest:
    """The only values visible to a caller-supplied detector."""

    stage: GuardrailStage
    content: str

    def __post_init__(self) -> None:
        if not isinstance(self.stage, GuardrailStage) or not isinstance(
            self.content, str
        ):
            raise _invalid_request()
        if any(0xD800 <= ord(item) <= 0xDFFF for item in self.content):
            raise _invalid_request()


@dataclass(frozen=True, slots=True)
class DetectorFinding:
    """One content-free detector decision and optional scalar ranges."""

    detector_id: str
    action: DetectorAction
    reason_code: str
    redaction_ranges: tuple[RedactionRange, ...] = ()

    def __post_init__(self) -> None:
        if (
            not _is_stable_id(self.detector_id)
            or not isinstance(self.action, DetectorAction)
            or not isinstance(self.reason_code, str)
            or _REASON_CODE.fullmatch(self.reason_code) is None
            or not isinstance(self.redaction_ranges, tuple)
            or any(not isinstance(item, RedactionRange) for item in self.redaction_ranges)
        ):
            raise _invalid_finding()
        if self.action is DetectorAction.REDACT:
            if not self.redaction_ranges:
                raise _invalid_finding()
            previous_end = -1
            for item in self.redaction_ranges:
                if item.start < previous_end:
                    raise _invalid_finding()
                previous_end = item.end
        elif self.redaction_ranges:
            raise _invalid_finding()

    def to_dict(self) -> dict[str, object]:
        return {
            "detectorId": self.detector_id,
            "action": self.action.value,
            "reasonCode": self.reason_code,
            "redactionRanges": [item.to_dict() for item in self.redaction_ranges],
        }


@dataclass(frozen=True, slots=True)
class GuardrailResult:
    """A deterministic decision that never includes raw input."""

    profile_id: str
    profile_version: str
    stage: GuardrailStage
    outcome: GuardrailOutcome
    reason_code: str
    detector_findings: tuple[DetectorFinding, ...]
    failed_detector_ids: tuple[str, ...]
    degraded: bool
    redacted_content: str | None

    def __post_init__(self) -> None:
        if (
            not _is_stable_id(self.profile_id)
            or not isinstance(self.profile_version, str)
            or _SEMVER.fullmatch(self.profile_version) is None
            or not isinstance(self.stage, GuardrailStage)
            or not isinstance(self.outcome, GuardrailOutcome)
            or not isinstance(self.reason_code, str)
            or _REASON_CODE.fullmatch(self.reason_code) is None
            or not isinstance(self.detector_findings, tuple)
            or any(
                not isinstance(item, DetectorFinding)
                for item in self.detector_findings
            )
            or not isinstance(self.failed_detector_ids, tuple)
            or any(not _is_stable_id(item) for item in self.failed_detector_ids)
            or len(set(self.failed_detector_ids)) != len(self.failed_detector_ids)
            or type(self.degraded) is not bool
            or self.degraded is not bool(self.failed_detector_ids)
        ):
            raise _invalid_finding()
        if self.outcome is GuardrailOutcome.REDACT:
            if (
                not isinstance(self.redacted_content, str)
                or REDACTION_TOKEN not in self.redacted_content
            ):
                raise _invalid_finding()
        elif self.redacted_content is not None:
            raise _invalid_finding()

    def to_dict(self) -> dict[str, object]:
        return {
            "profileId": self.profile_id,
            "profileVersion": self.profile_version,
            "stage": self.stage.value,
            "outcome": self.outcome.value,
            "reasonCode": self.reason_code,
            "detectorFindings": [item.to_dict() for item in self.detector_findings],
            "failedDetectorIds": list(self.failed_detector_ids),
            "degraded": self.degraded,
            "redactedContent": self.redacted_content,
        }

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )


@runtime_checkable
class GuardrailDetector(Protocol):
    """Caller-owned synchronous local detector interface."""

    detector_id: str

    def evaluate(self, request: GuardrailRequest) -> DetectorFinding:
        """Inspect one local request without retaining it."""


def _validate_finding(
    finding: object,
    detector_id: str,
    scalar_length: int,
) -> DetectorFinding:
    if not isinstance(finding, DetectorFinding) or finding.detector_id != detector_id:
        raise _invalid_finding()
    if any(item.end > scalar_length for item in finding.redaction_ranges):
        raise _invalid_finding()
    return finding


def _merge_ranges(findings: Sequence[DetectorFinding]) -> tuple[RedactionRange, ...]:
    candidates = sorted(
        (
            item
            for finding in findings
            if finding.action is DetectorAction.REDACT
            for item in finding.redaction_ranges
        ),
        key=lambda item: (item.start, item.end),
    )
    merged: list[RedactionRange] = []
    for item in candidates:
        if not merged or item.start > merged[-1].end:
            merged.append(item)
            continue
        previous = merged[-1]
        merged[-1] = RedactionRange(previous.start, max(previous.end, item.end))
    return tuple(merged)


def _redact(content: str, findings: Sequence[DetectorFinding]) -> str:
    scalars = list(content)
    ranges = _merge_ranges(findings)
    output: list[str] = []
    cursor = 0
    for item in ranges:
        output.extend(scalars[cursor:item.start])
        output.append(REDACTION_TOKEN)
        cursor = item.end
    output.extend(scalars[cursor:])
    return "".join(output)


class GuardrailClient:
    """A profile-bound local evaluator with no transport or persistence."""

    __slots__ = ("_detectors", "_profile")

    def __init__(
        self,
        profile: GuardrailProfile,
        detectors: Sequence[GuardrailDetector],
    ) -> None:
        if not isinstance(profile, GuardrailProfile):
            raise _invalid_profile()
        if isinstance(detectors, (str, bytes, bytearray)) or not isinstance(
            detectors, Sequence
        ):
            raise GuardrailContractError("UNKNOWN_DETECTOR")
        registered: dict[str, GuardrailDetector] = {}
        for detector in detectors:
            try:
                detector_id = detector.detector_id
                evaluate = detector.evaluate
            except (AttributeError, TypeError):
                detector_id = None
                evaluate = None
            if (
                not _is_stable_id(detector_id)
                or detector_id in registered
                or not callable(evaluate)
                or inspect.iscoroutinefunction(evaluate)
            ):
                raise GuardrailContractError("UNKNOWN_DETECTOR")
            registered[detector_id] = detector
        if set(registered) != set(profile.detector_ids):
            raise GuardrailContractError("UNKNOWN_DETECTOR")
        self._profile = profile
        self._detectors = MappingProxyType(registered)

    @property
    def profile(self) -> GuardrailProfile:
        return self._profile

    def _result(
        self,
        *,
        outcome: GuardrailOutcome,
        reason_code: str,
        findings: Sequence[DetectorFinding] = (),
        failed: Sequence[str] = (),
        redacted_content: str | None = None,
    ) -> GuardrailResult:
        return GuardrailResult(
            profile_id=self._profile.profile_id,
            profile_version=self._profile.version,
            stage=self._profile.stage,
            outcome=outcome,
            reason_code=reason_code,
            detector_findings=tuple(findings),
            failed_detector_ids=tuple(failed),
            degraded=bool(failed),
            redacted_content=redacted_content,
        )

    def evaluate(self, content: str) -> GuardrailResult:
        """Evaluate bounded local content in declared detector order."""

        if not isinstance(content, str):
            raise _invalid_request()
        if any(0xD800 <= ord(item) <= 0xDFFF for item in content):
            raise _invalid_request()
        content_size = len(content.encode("utf-8"))
        if content_size > self._profile.maximum_content_bytes:
            return self._result(
                outcome=GuardrailOutcome.DENY,
                reason_code="PAYLOAD_TOO_LARGE",
            )

        request = GuardrailRequest(stage=self._profile.stage, content=content)
        scalar_length = len(content)
        findings: list[DetectorFinding] = []
        failed: list[str] = []
        for detector_id in self._profile.detector_ids:
            detector = self._detectors[detector_id]
            try:
                finding = _validate_finding(
                    detector.evaluate(request),
                    detector_id,
                    scalar_length,
                )
            except Exception:
                failed.append(detector_id)
                if self._profile.fail_mode is FailMode.FAIL_CLOSED:
                    return self._result(
                        outcome=GuardrailOutcome.ERROR_FAIL_CLOSED,
                        reason_code="DETECTOR_FAILURE",
                        findings=findings,
                        failed=failed,
                    )
                continue
            findings.append(finding)

        precedence = (
            (DetectorAction.DENY, GuardrailOutcome.DENY),
            (DetectorAction.QUARANTINE, GuardrailOutcome.QUARANTINE),
            (DetectorAction.REDACT, GuardrailOutcome.REDACT),
        )
        for action, outcome in precedence:
            winner = next((item for item in findings if item.action is action), None)
            if winner is None:
                continue
            return self._result(
                outcome=outcome,
                reason_code=winner.reason_code,
                findings=findings,
                failed=failed,
                redacted_content=(
                    _redact(content, findings)
                    if outcome is GuardrailOutcome.REDACT
                    else None
                ),
            )
        if failed:
            return self._result(
                outcome=GuardrailOutcome.ERROR_FAIL_OPEN,
                reason_code="DETECTOR_FAILURE_FAIL_OPEN",
                findings=findings,
                failed=failed,
            )
        winner = findings[0]
        return self._result(
            outcome=GuardrailOutcome.ALLOW,
            reason_code=winner.reason_code,
            findings=findings,
        )

    def stream(self) -> GuardrailStream:
        """Create a profile-bound cumulative stream."""

        if self._profile.stage is not GuardrailStage.STREAMING:
            raise _invalid_profile()
        return GuardrailStream(self)


class GuardrailStream:
    """Bounded cumulative streaming evaluation with explicit terminal state."""

    __slots__ = ("_buffer", "_client", "_finished", "_last_result", "_terminal")

    _TERMINAL_OUTCOMES = frozenset(
        {
            GuardrailOutcome.DENY,
            GuardrailOutcome.QUARANTINE,
            GuardrailOutcome.ERROR_FAIL_CLOSED,
        }
    )

    def __init__(self, client: GuardrailClient) -> None:
        if (
            not isinstance(client, GuardrailClient)
            or client.profile.stage is not GuardrailStage.STREAMING
        ):
            raise _invalid_profile()
        self._client = client
        self._buffer = ""
        self._last_result: GuardrailResult | None = None
        self._terminal = False
        self._finished = False

    def _require_open(self) -> None:
        if self._finished:
            raise GuardrailContractError("STREAM_FINISHED")
        if self._terminal:
            raise GuardrailContractError("STREAM_TERMINATED")

    def push(self, chunk: str) -> GuardrailResult:
        self._require_open()
        if not isinstance(chunk, str) or not chunk:
            raise _invalid_request()
        candidate = self._buffer + chunk
        result = self._client.evaluate(candidate)
        self._last_result = result
        if result.outcome in self._TERMINAL_OUTCOMES:
            self._buffer = ""
            self._terminal = True
        else:
            self._buffer = candidate
        return result

    def finish(self) -> GuardrailResult:
        self._require_open()
        result = (
            self._last_result
            if self._last_result is not None
            else self._client.evaluate("")
        )
        self._buffer = ""
        self._finished = True
        return result
