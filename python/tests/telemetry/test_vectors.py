from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Iterator


PYTHON_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = PYTHON_ROOT.parent
sys.path.insert(0, str(PYTHON_ROOT / "src"))

from planeon_harness.context import HarnessContext, use_context  # noqa: E402
from planeon_harness.decorators import InMemorySpanSink, instrument  # noqa: E402


class Clock:
    def __init__(self, values: list[int]) -> None:
        self._values: Iterator[int] = iter(values)

    def __call__(self) -> int:
        return next(self._values)


class GoldenVectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (REPOSITORY_ROOT / "examples" / "telemetry" / "golden-span-vectors.json").read_text(
                encoding="utf-8"
            )
        )

    def parent(self) -> HarnessContext:
        parent = self.document["parentContext"]
        return HarnessContext(
            trace_id=parent["traceId"],
            span_id=parent["spanId"],
            trace_flags=parent["traceFlags"],
            tenant_id=parent["tenantId"],
            organization_id=parent["organizationId"],
            harness_id=parent["harnessId"],
            plane_id=parent["planeId"],
            operation_id=parent["operationId"],
            correlation_id=parent["correlationId"],
        )

    def test_python_matches_every_cross_language_vector(self) -> None:
        for vector in self.document["vectors"]:
            with self.subTest(vector=vector["id"]):
                specification = vector["input"]
                sink = InMemorySpanSink()

                @instrument(
                    specification["operationName"],
                    operation_kind=specification["operationKind"],
                    attributes=specification["attributes"],
                    sink=sink,
                    clock_ns=Clock(specification["clock"]),
                    span_id_factory=lambda value=specification["spanId"]: value,
                    error_type=lambda error, value=specification.get("errorType", "error"): value,
                )
                def operation() -> str:
                    if "errorType" in specification:
                        raise ValueError("fixture-message-that-must-not-be-exported")
                    return "accepted"

                try:
                    with use_context(self.parent()):
                        operation()
                except ValueError:
                    pass
                self.assertEqual(sink.records[0].to_dict(), vector["expected"])
                self.assertNotIn(
                    "fixture-message-that-must-not-be-exported",
                    sink.records[0].canonical_json(),
                )


if __name__ == "__main__":
    unittest.main()
