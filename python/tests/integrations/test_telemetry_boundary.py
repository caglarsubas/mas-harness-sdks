from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "python" / "src"))

from planeon_harness.context import HarnessContext, use_context  # noqa: E402
from planeon_harness.decorators import InMemorySpanSink  # noqa: E402
from planeon_harness.integrations import (  # noqa: E402
    IntegrationContractError,
    instrument_async_vector_search,
    instrument_vector_search,
)


class SensitiveFrameworkFailure(RuntimeError):
    pass


class TelemetryBoundaryTests(unittest.TestCase):
    def context(self) -> HarnessContext:
        return HarnessContext.create(
            trace_id="1" * 32,
            span_id="2" * 16,
            tenant_id="tenant-local",
            organization_id="organization-local",
        )

    def test_vector_wrappers_preserve_results_and_emit_no_content(self) -> None:
        private_argument = "PRIVATE_PROMPT_CONTENT"
        private_result = "PRIVATE_VECTOR_RESULT"
        sink = InMemorySpanSink()

        def search(query: str) -> str:
            self.assertEqual(query, private_argument)
            return private_result

        async def asearch(query: str) -> str:
            self.assertEqual(query, private_argument)
            return private_result

        wrapped = instrument_vector_search(search, sink=sink)
        async_wrapped = instrument_async_vector_search(asearch, sink=sink)
        with use_context(self.context()):
            self.assertEqual(wrapped(private_argument), private_result)
            self.assertEqual(asyncio.run(async_wrapped(private_argument)), private_result)

        evidence = json.dumps(
            [record.to_dict() for record in sink.records],
            sort_keys=True,
            separators=(",", ":"),
        )
        self.assertNotIn(private_argument, evidence)
        self.assertNotIn(private_result, evidence)
        self.assertIn("tenant-local", evidence)
        self.assertIn("organization-local", evidence)
        self.assertEqual(
            [record.name for record in sink.records],
            [
                "harness.integration.vector.search",
                "harness.integration.vector.asearch",
            ],
        )

    def test_framework_exception_identity_is_preserved_without_message_capture(self) -> None:
        private_message = "PRIVATE_EXCEPTION_MESSAGE"
        failure = SensitiveFrameworkFailure(private_message)
        sink = InMemorySpanSink()

        def search(_query: str) -> object:
            raise failure

        wrapped = instrument_vector_search(search, sink=sink)
        with self.assertRaises(SensitiveFrameworkFailure) as caught:
            wrapped("PRIVATE_ARGUMENT")
        self.assertIs(caught.exception, failure)
        evidence = sink.records[0].canonical_json()
        self.assertNotIn(private_message, evidence)
        self.assertNotIn("PRIVATE_ARGUMENT", evidence)
        self.assertEqual(sink.records[0].status_code, "ERROR")

    def test_sync_and_async_vector_contracts_fail_closed(self) -> None:
        async def asearch():
            return None

        def search():
            return None

        for factory, function in (
            (instrument_vector_search, asearch),
            (instrument_async_vector_search, search),
        ):
            with self.assertRaises(IntegrationContractError) as caught:
                factory(function)
            self.assertEqual(caught.exception.code, "INVALID_INTEGRATION_SURFACE")


if __name__ == "__main__":
    unittest.main()
