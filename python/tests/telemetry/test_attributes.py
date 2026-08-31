from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path


PYTHON_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = PYTHON_ROOT.parent
sys.path.insert(0, str(PYTHON_ROOT / "src"))

from planeon_harness.attributes import (  # noqa: E402
    OPERATION_KINDS,
    SEMANTIC_ATTRIBUTE_KEYS,
    SENSITIVE_KEY_SEGMENTS,
    AttributeValidationError,
    context_attributes,
    sanitize_attributes,
)
from planeon_harness.context import HarnessContext  # noqa: E402


class AttributeTests(unittest.TestCase):
    def test_public_attribute_contract_matches_python_constants(self) -> None:
        contract = json.loads(
            (REPOSITORY_ROOT / "examples" / "telemetry" / "attribute-contract.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(contract["keys"], dict(SEMANTIC_ATTRIBUTE_KEYS))
        self.assertEqual(contract["operationKinds"], sorted(OPERATION_KINDS))
        self.assertEqual(contract["sensitiveKeySegments"], sorted(SENSITIVE_KEY_SEGMENTS))

    def test_sensitive_unknown_and_unsafe_values_are_dropped(self) -> None:
        sanitized = sanitize_attributes(
            {
                "harness.label.accepted": "yes",
                "harness.label.numbers": [1, 2, 3],
                "harness.label.mixed": [1, "two"],
                "harness.label.nested": {"value": "no"},
                "harness.label.long": "x" * 257,
                "harness.label.nan": math.nan,
                "harness.label.note": "free text is not an opaque label",
                "harness.label.raw_prompt": "fixture-secret",
                "harness.label.api_key": "fixture-key",
                "gen_ai.prompt": "fixture-secret",
                "other.value": "unknown",
            }
        )
        self.assertEqual(
            dict(sanitized.values),
            {
                "harness.label.accepted": "yes",
                "harness.label.numbers": (1, 2, 3),
            },
        )
        self.assertEqual(sanitized.dropped_count, 9)
        self.assertNotIn("fixture-secret", repr(sanitized))
        self.assertNotIn("raw_prompt", repr(sanitized))
        self.assertNotIn("api_key", repr(sanitized))

    def test_context_attributes_are_tenant_neutral_and_sorted(self) -> None:
        context = HarnessContext(
            trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
            span_id="00f067aa0ba902b7",
            tenant_id="tenant-a",
            plane_id="knowledge",
        )
        attributes = context_attributes(
            context,
            operation_name="harness.domain.resolve",
            operation_kind="INTERNAL",
            outcome="success",
        )
        self.assertEqual(list(attributes), sorted(attributes))
        self.assertEqual(attributes["harness.tenant.id"], "tenant-a")
        self.assertFalse(any(key.startswith("gen_ai.") for key in attributes))

    def test_invalid_operation_contract_fails_closed(self) -> None:
        context = HarnessContext(
            trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
            span_id="00f067aa0ba902b7",
        )
        with self.assertRaises(AttributeValidationError):
            context_attributes(
                context,
                operation_name="Contains Spaces",
                operation_kind="INTERNAL",
                outcome="success",
            )
        with self.assertRaises(AttributeValidationError):
            context_attributes(
                context,
                operation_name="harness.valid",
                operation_kind="REMOTE",
                outcome="success",
            )


if __name__ == "__main__":
    unittest.main()
