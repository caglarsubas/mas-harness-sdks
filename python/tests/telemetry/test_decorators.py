from __future__ import annotations

import sys
import unittest
from pathlib import Path


PYTHON_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(PYTHON_SRC))

from planeon_harness.context import HarnessContext, current_context, use_context  # noqa: E402
from planeon_harness.decorators import InMemorySpanSink, SpanRecord, instrument  # noqa: E402


class Clock:
    def __init__(self, *values: int) -> None:
        self._values = iter(values)

    def __call__(self) -> int:
        return next(self._values)


def parent_context() -> HarnessContext:
    return HarnessContext(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        trace_flags="01",
        tenant_id="tenant-a",
    )


class DecoratorTests(unittest.TestCase):
    def test_sync_decorator_propagates_child_without_capturing_arguments(self) -> None:
        sink = InMemorySpanSink()

        @instrument(
            "harness.sync.execute",
            sink=sink,
            clock_ns=Clock(10, 20),
            span_id_factory=lambda: "1111111111111111",
        )
        def execute(secret_argument: str) -> str:
            active = current_context(required=True)
            assert active is not None
            self.assertEqual(active.span_id, "1111111111111111")
            return secret_argument

        with use_context(parent_context()):
            self.assertEqual(execute("must-not-appear"), "must-not-appear")
        record = sink.records[0]
        self.assertEqual(record.parent_span_id, "00f067aa0ba902b7")
        self.assertNotIn("must-not-appear", record.canonical_json())

    def test_error_records_type_without_message_or_stack(self) -> None:
        sink = InMemorySpanSink()

        @instrument(
            "harness.sync.fail",
            sink=sink,
            clock_ns=Clock(10, 30),
            span_id_factory=lambda: "1111111111111111",
            error_type=lambda error: "validation_error",
        )
        def fail() -> None:
            raise ValueError("must-not-appear")

        with self.assertRaisesRegex(ValueError, "must-not-appear"):
            with use_context(parent_context()):
                fail()
        record = sink.records[0]
        encoded = record.canonical_json()
        self.assertEqual(record.status_code, "ERROR")
        self.assertIn('"error.type":"validation_error"', encoded)
        self.assertNotIn("must-not-appear", encoded)

    def test_default_sink_has_no_observable_side_effect(self) -> None:
        @instrument(
            "harness.null.execute",
            clock_ns=Clock(1, 2),
            span_id_factory=lambda: "1111111111111111",
        )
        def execute() -> int:
            return 7

        self.assertEqual(execute(), 7)

    def test_sink_failure_is_isolated_unless_strict(self) -> None:
        class FailingSink:
            def emit(self, record: SpanRecord) -> None:
                del record
                raise RuntimeError("sink unavailable")

        @instrument(
            "harness.sink.isolated",
            sink=FailingSink(),
            clock_ns=Clock(1, 2),
            span_id_factory=lambda: "1111111111111111",
        )
        def isolated() -> str:
            return "business-result"

        self.assertEqual(isolated(), "business-result")

        @instrument(
            "harness.sink.strict",
            sink=FailingSink(),
            strict_sink=True,
            clock_ns=Clock(1, 2),
            span_id_factory=lambda: "1111111111111111",
        )
        def strict() -> str:
            return "business-result"

        with self.assertRaisesRegex(RuntimeError, "sink unavailable"):
            strict()

    def test_strict_sink_never_masks_business_failure(self) -> None:
        class FailingSink:
            def emit(self, record: SpanRecord) -> None:
                del record
                raise RuntimeError("sink unavailable")

        @instrument(
            "harness.sink.business_failure",
            sink=FailingSink(),
            strict_sink=True,
            clock_ns=Clock(1, 2),
            span_id_factory=lambda: "1111111111111111",
        )
        def fail() -> None:
            raise ValueError("business failure")

        with self.assertRaisesRegex(ValueError, "business failure"):
            fail()

    def test_error_classifier_failure_never_masks_business_failure(self) -> None:
        sink = InMemorySpanSink()

        def broken_classifier(error: BaseException) -> str:
            del error
            raise RuntimeError("classifier failure")

        @instrument(
            "harness.classifier.business_failure",
            sink=sink,
            clock_ns=Clock(1, 2),
            span_id_factory=lambda: "1111111111111111",
            error_type=broken_classifier,
        )
        def fail() -> None:
            raise ValueError("business failure")

        with self.assertRaisesRegex(ValueError, "business failure"):
            fail()
        self.assertEqual(sink.records[0].attributes["error.type"], "error")


class AsyncDecoratorTests(unittest.IsolatedAsyncioTestCase):
    async def test_async_decorator_preserves_task_local_context(self) -> None:
        sink = InMemorySpanSink()

        @instrument(
            "harness.async.execute",
            operation_kind="CLIENT",
            sink=sink,
            clock_ns=Clock(100, 150),
            span_id_factory=lambda: "2222222222222222",
        )
        async def execute() -> str:
            active = current_context(required=True)
            assert active is not None
            self.assertEqual(active.span_id, "2222222222222222")
            return "accepted"

        with use_context(parent_context()):
            self.assertEqual(await execute(), "accepted")
        self.assertEqual(sink.records[0].kind, "CLIENT")


if __name__ == "__main__":
    unittest.main()
