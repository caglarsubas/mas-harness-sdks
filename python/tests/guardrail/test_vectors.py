from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "python" / "src"))

from planeon_harness.guardrail import (  # noqa: E402
    DetectorAction,
    DetectorFinding,
    GuardrailClient,
    GuardrailContractError,
    GuardrailProfile,
    GuardrailRequest,
    RedactionRange,
)


VECTORS = json.loads(
    (ROOT / "fixtures" / "guardrail" / "conformance-vectors.json").read_text(
        encoding="utf-8"
    )
)


class PrivateDetectorFailure(RuntimeError):
    pass


class FixtureDetector:
    def __init__(self, specification: dict[str, object]) -> None:
        self.detector_id = specification["detectorId"]
        self.specification = specification
        self.calls = 0

    def evaluate(self, request: GuardrailRequest) -> DetectorFinding:
        self.calls += 1
        behavior = self.specification["behavior"]
        if behavior == "THROW":
            raise PrivateDetectorFailure("PRIVATE_DETECTOR_EXCEPTION")
        if behavior == "MALFORMED":
            return {  # type: ignore[return-value]
                "detectorId": self.detector_id,
                "content": request.content,
            }
        if behavior == "ALLOW":
            return DetectorFinding(
                detector_id=self.detector_id,
                action=DetectorAction.ALLOW,
                reason_code="NO_MATCH",
            )
        if behavior == "ACTION":
            return DetectorFinding(
                detector_id=self.detector_id,
                action=DetectorAction(self.specification["action"]),
                reason_code=self.specification["reasonCode"],
                redaction_ranges=tuple(
                    RedactionRange(item["start"], item["end"])
                    for item in self.specification.get("redactionRanges", [])
                ),
            )
        if behavior != "PATTERN":
            raise AssertionError("unknown fixture detector behavior")

        scalars = list(request.content)
        pattern = list(self.specification["pattern"])
        ranges: list[RedactionRange] = []
        index = 0
        while index <= len(scalars) - len(pattern):
            if scalars[index : index + len(pattern)] == pattern:
                ranges.append(RedactionRange(index, index + len(pattern)))
                index += len(pattern)
            else:
                index += 1
        if not ranges:
            return DetectorFinding(
                detector_id=self.detector_id,
                action=DetectorAction.ALLOW,
                reason_code="NO_MATCH",
            )
        action = DetectorAction(self.specification["action"])
        return DetectorFinding(
            detector_id=self.detector_id,
            action=action,
            reason_code=self.specification["reasonCode"],
            redaction_ranges=(
                tuple(ranges) if action is DetectorAction.REDACT else ()
            ),
        )


def canonical(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


class GuardrailVectorTests(unittest.TestCase):
    def detectors(
        self, vector: dict[str, object]
    ) -> tuple[list[FixtureDetector], dict[str, FixtureDetector]]:
        created = [FixtureDetector(item) for item in vector["detectors"]]
        return created, {item.detector_id: item for item in created}

    def assert_result(
        self,
        result,
        expected: dict[str, object],
        protected_content: str | None = None,
    ) -> None:
        self.assertEqual(result.to_dict(), expected)
        self.assertEqual(result.canonical_json(), canonical(expected))
        if protected_content:
            self.assertNotIn(protected_content, result.canonical_json())

    def assert_closed_error(self, action, code: str, private_value: str = "") -> None:
        with self.assertRaises(GuardrailContractError) as caught:
            action()
        self.assertEqual(caught.exception.code, code)
        if private_value:
            self.assertNotIn(private_value, str(caught.exception))
        self.assertNotIn("PRIVATE_", str(caught.exception))

    def test_shared_conformance_vectors(self) -> None:
        self.assertEqual(
            VECTORS["schemaVersion"],
            "harness.planeon.ai/guardrail-conformance/v1",
        )
        for vector in VECTORS["vectors"]:
            with self.subTest(vector=vector["id"]):
                if vector["kind"] == "PROFILE_ERROR":
                    self.assert_closed_error(
                        lambda: GuardrailProfile.from_dict(vector["profile"]),
                        vector["expectedError"],
                        "PRIVATE_PROFILE_FIELD",
                    )
                    continue

                profile = GuardrailProfile.from_dict(vector["profile"])
                detectors, by_id = self.detectors(vector)
                if vector["kind"] == "CONSTRUCTION_ERROR":
                    self.assert_closed_error(
                        lambda: GuardrailClient(profile, detectors),
                        vector["expectedError"],
                    )
                    self.assertTrue(all(item.calls == 0 for item in detectors))
                    continue

                client = GuardrailClient(profile, detectors)
                self.assertTrue(all(item.calls == 0 for item in detectors))
                if vector["kind"] == "STREAM_CREATION_ERROR":
                    self.assert_closed_error(
                        client.stream,
                        vector["expectedError"],
                    )
                    continue

                if vector["kind"] == "EVALUATE":
                    result = client.evaluate(vector["content"])
                    self.assert_result(
                        result,
                        vector["expectedResult"],
                        vector["content"],
                    )
                    if vector["id"] == "utf8-byte-limit-before-detector":
                        self.assertEqual(by_id["detector.failure"].calls, 0)
                    continue

                self.assertEqual(vector["kind"], "STREAM")
                stream = client.stream()
                actual_results = []
                accumulated = ""
                for chunk, expected in zip(
                    vector["chunks"],
                    vector["expectedPushResults"],
                    strict=True,
                ):
                    accumulated += chunk
                    result = stream.push(chunk)
                    actual_results.append(result.to_dict())
                    self.assert_result(result, expected, accumulated)
                self.assertEqual(
                    actual_results,
                    vector["expectedPushResults"],
                )
                if vector.get("finish"):
                    result = stream.finish()
                    self.assert_result(
                        result,
                        vector["expectedFinishResult"],
                        accumulated,
                    )
                after = vector.get("afterCall")
                if after is not None:
                    if after["method"] == "PUSH":
                        action = lambda: stream.push(after["value"])
                        private_value = after["value"]
                    else:
                        action = stream.finish
                        private_value = ""
                    self.assert_closed_error(
                        action,
                        vector["expectedError"],
                        private_value,
                    )

    def test_expected_outputs_never_repeat_raw_vector_content(self) -> None:
        for vector in VECTORS["vectors"]:
            expected = canonical(
                {
                    key: value
                    for key, value in vector.items()
                    if key.startswith("expected")
                }
            )
            content = vector.get("content")
            if isinstance(content, str) and content:
                self.assertNotIn(content, expected)
            chunks = vector.get("chunks")
            if isinstance(chunks, list) and chunks:
                self.assertNotIn("".join(chunks), expected)
            self.assertNotIn("PRIVATE_DETECTOR_EXCEPTION", expected)


if __name__ == "__main__":
    unittest.main()
