from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "python" / "src"))

from planeon_harness.guardrail import (  # noqa: E402
    API_VERSION,
    PROFILE_KIND,
    DetectorAction,
    DetectorFinding,
    FailMode,
    GuardrailClient,
    GuardrailContractError,
    GuardrailProfile,
    GuardrailRequest,
    GuardrailStage,
    GuardrailStream,
)


class AllowDetector:
    detector_id = "detector.allow"

    def __init__(self) -> None:
        self.calls = 0

    def evaluate(self, request: GuardrailRequest) -> DetectorFinding:
        self.calls += 1
        return DetectorFinding(
            detector_id=self.detector_id,
            action=DetectorAction.ALLOW,
            reason_code="NO_MATCH",
        )


class ThrowingDetector:
    detector_id = "detector.throwing"

    def evaluate(self, request: GuardrailRequest) -> DetectorFinding:
        raise RuntimeError(f"PRIVATE_EXCEPTION:{request.content}")


class AsyncDetector:
    detector_id = "detector.async"

    async def evaluate(self, request: GuardrailRequest) -> DetectorFinding:
        raise AssertionError(request.content)


class ExtraDetector(AllowDetector):
    detector_id = "detector.extra"


class ExplodingRegistrationDetector:
    @property
    def detector_id(self) -> str:
        raise AttributeError("PRIVATE_REGISTRATION_DETAIL")


def profile(
    detector_ids: tuple[str, ...],
    *,
    fail_mode: FailMode = FailMode.FAIL_CLOSED,
    stage: GuardrailStage = GuardrailStage.INPUT,
) -> GuardrailProfile:
    return GuardrailProfile(
        api_version=API_VERSION,
        kind=PROFILE_KIND,
        profile_id="profile.security",
        version="1.0.0",
        stage=stage,
        fail_mode=fail_mode,
        maximum_content_bytes=1024,
        detector_ids=detector_ids,
    )


class GuardrailSecurityTests(unittest.TestCase):
    def test_detector_failure_has_no_content_or_console_side_effect(self) -> None:
        client = GuardrailClient(
            profile(("detector.throwing",)),
            [ThrowingDetector()],
        )
        private = "PRIVATE_PROTECTED_CONTENT"
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = client.evaluate(private)
        evidence = json.dumps(result.to_dict(), sort_keys=True)
        self.assertEqual(result.outcome.value, "ERROR_FAIL_CLOSED")
        self.assertNotIn(private, evidence)
        self.assertNotIn("PRIVATE_EXCEPTION", evidence)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")

    def test_registration_is_exact_and_construction_invokes_nothing(self) -> None:
        detector = AllowDetector()
        GuardrailClient(profile(("detector.allow",)), [detector])
        self.assertEqual(detector.calls, 0)
        for declared, detectors in (
            (("detector.allow",), [detector, detector]),
            (("detector.async",), [AsyncDetector()]),
            (("detector.missing",), []),
            (("detector.allow",), [detector, ExtraDetector()]),
            (("detector.exploding",), [ExplodingRegistrationDetector()]),
        ):
            with self.subTest(detectors=detectors):
                with self.assertRaises(GuardrailContractError) as caught:
                    GuardrailClient(profile(declared), detectors)
                self.assertEqual(caught.exception.code, "UNKNOWN_DETECTOR")
                self.assertIsNone(caught.exception.__cause__)
                self.assertIsNone(caught.exception.__context__)

    def test_public_objects_are_frozen_and_result_shape_is_closed(self) -> None:
        declared = profile(("detector.allow",))
        with self.assertRaises(FrozenInstanceError):
            declared.version = "2.0.0"  # type: ignore[misc]
        result = GuardrailClient(declared, [AllowDetector()]).evaluate("PRIVATE")
        self.assertEqual(
            set(result.to_dict()),
            {
                "profileId",
                "profileVersion",
                "stage",
                "outcome",
                "reasonCode",
                "detectorFindings",
                "failedDetectorIds",
                "degraded",
                "redactedContent",
            },
        )
        self.assertNotIn("PRIVATE", result.canonical_json())

    def test_invalid_requests_and_stream_states_use_fixed_errors(self) -> None:
        client = GuardrailClient(profile(("detector.allow",)), [AllowDetector()])
        with self.assertRaises(GuardrailContractError) as caught:
            client.evaluate(object())  # type: ignore[arg-type]
        self.assertEqual(caught.exception.code, "INVALID_GUARDRAIL_REQUEST")
        self.assertEqual(str(caught.exception), "guardrail request is invalid")
        with self.assertRaises(GuardrailContractError) as caught:
            client.evaluate("\ud800PRIVATE_PROTECTED_CONTENT")
        self.assertEqual(caught.exception.code, "INVALID_GUARDRAIL_REQUEST")
        self.assertIsNone(caught.exception.__cause__)
        self.assertIsNone(caught.exception.__context__)
        with self.assertRaises(GuardrailContractError) as caught:
            GuardrailStream(client)
        self.assertEqual(caught.exception.code, "INVALID_GUARDRAIL_PROFILE")

        streaming = GuardrailClient(
            profile(("detector.allow",), stage=GuardrailStage.STREAMING),
            [AllowDetector()],
        ).stream()
        streaming.finish()
        with self.assertRaises(GuardrailContractError) as caught:
            streaming.finish()
        self.assertEqual(caught.exception.code, "STREAM_FINISHED")

    def test_error_codes_reject_inherited_object_keys(self) -> None:
        with self.assertRaises(ValueError) as caught:
            GuardrailContractError("toString")
        self.assertEqual(str(caught.exception), "unknown guardrail error code")


if __name__ == "__main__":
    unittest.main()
