from __future__ import annotations

import sys
import unittest
from pathlib import Path


PYTHON_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(PYTHON_SRC))

from planeon_harness.context import (  # noqa: E402
    ContextValidationError,
    HarnessContext,
    current_context,
    extract_context,
    format_traceparent,
    inject_context,
    parse_traceparent,
    use_context,
)


TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"
SPAN_ID = "00f067aa0ba902b7"


class ContextTests(unittest.TestCase):
    def context(self) -> HarnessContext:
        return HarnessContext(
            trace_id=TRACE_ID,
            span_id=SPAN_ID,
            trace_flags="01",
            tenant_id="tenant-a",
            organization_id="org-a",
            harness_id="knowledge.domain-semantic",
            plane_id="knowledge",
            operation_id="op-123",
            correlation_id="corr-456",
        )

    def test_traceparent_round_trip(self) -> None:
        context = self.context()
        value = format_traceparent(context)
        self.assertEqual(value, f"00-{TRACE_ID}-{SPAN_ID}-01")
        self.assertEqual(parse_traceparent(value), (TRACE_ID, SPAN_ID, "01"))

    def test_invalid_traceparent_is_ignored_or_strictly_rejected(self) -> None:
        carrier = {"traceparent": f"00-{'0' * 32}-{SPAN_ID}-01"}
        self.assertIsNone(extract_context(carrier))
        with self.assertRaises(ContextValidationError):
            extract_context(carrier, strict=True)

    def test_identity_requires_explicit_trust_on_inject_and_extract(self) -> None:
        context = self.context()
        trace_only = inject_context(context)
        self.assertEqual(set(trace_only), {"traceparent"})
        trusted = inject_context(context, include_identity=True)
        self.assertEqual(trusted["x-harness-tenant-id"], "tenant-a")
        untrusted_result = extract_context(trusted)
        self.assertIsNotNone(untrusted_result)
        assert untrusted_result is not None
        self.assertIsNone(untrusted_result.tenant_id)
        trusted_result = extract_context(trusted, trust_identity=True, strict=True)
        self.assertEqual(trusted_result, context)

    def test_case_insensitive_duplicate_carrier_is_rejected(self) -> None:
        carrier = {
            "TraceParent": f"00-{TRACE_ID}-{SPAN_ID}-01",
            "traceparent": f"00-{TRACE_ID}-{SPAN_ID}-01",
        }
        with self.assertRaises(ContextValidationError):
            extract_context(carrier, strict=True)

    def test_context_scope_restores_parent(self) -> None:
        parent = self.context()
        child = parent.child(span_id="1111111111111111")
        self.assertIsNone(current_context())
        with use_context(parent):
            self.assertIs(current_context(), parent)
            with use_context(child):
                self.assertIs(current_context(), child)
            self.assertIs(current_context(), parent)
        self.assertIsNone(current_context())

    def test_opaque_identity_rejects_whitespace(self) -> None:
        with self.assertRaises(ContextValidationError):
            HarnessContext(trace_id=TRACE_ID, span_id=SPAN_ID, tenant_id="tenant a")

    def test_explicit_empty_ids_are_rejected_instead_of_replaced(self) -> None:
        with self.assertRaises(ContextValidationError):
            HarnessContext.create(trace_id="", span_id=SPAN_ID)
        with self.assertRaises(ContextValidationError):
            self.context().child(span_id="")

    def test_non_string_identity_is_rejected_as_context_validation(self) -> None:
        with self.assertRaises(ContextValidationError):
            HarnessContext(trace_id=TRACE_ID, span_id=SPAN_ID, tenant_id=7)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
