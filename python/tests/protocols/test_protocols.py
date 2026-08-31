from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "python" / "src"))

from planeon_harness.protocols import (  # noqa: E402
    MCP_COMPATIBILITY,
    MCP_CURRENT,
    ProtocolHelperError,
    build_mcp_request,
    build_sse_resume_headers,
    classify_a2a_task_state,
    classify_mcp_task_state,
    negotiate_mcp_version,
    serialize_harness_cloud_event,
    validate_harness_cloud_event,
)


VECTORS = json.loads(
    (ROOT / "fixtures" / "protocols" / "golden-vectors.json").read_text(encoding="utf-8")
)


def mcp_request(raw: dict[str, object]):
    return build_mcp_request(
        version=raw["version"],
        request_id=raw["requestId"],
        method=raw["method"],
        params=raw["params"],
        client_name=raw.get("clientName"),
        client_version=raw.get("clientVersion"),
        client_capabilities=raw.get("clientCapabilities"),
        session_id=raw.get("sessionId"),
    )


class ProtocolVectorTests(unittest.TestCase):
    def test_current_mcp_vector_is_stateless_and_self_describing(self) -> None:
        raw = copy.deepcopy(VECTORS["mcp"]["current"]["input"])
        original = copy.deepcopy(raw)
        self.assertEqual(mcp_request(raw), VECTORS["mcp"]["current"]["expected"])
        self.assertEqual(raw, original)
        self.assertNotIn("Mcp-Session-Id", mcp_request(raw)["headers"])

    def test_compatibility_mcp_vector_requires_explicit_session(self) -> None:
        raw = VECTORS["mcp"]["compatibility"]["input"]
        self.assertEqual(mcp_request(raw), VECTORS["mcp"]["compatibility"]["expected"])
        self.assertNotIn("Mcp-Method", mcp_request(raw)["headers"])

    def test_version_negotiation_is_exact_and_prefer_current(self) -> None:
        self.assertEqual(negotiate_mcp_version([MCP_COMPATIBILITY, MCP_CURRENT]), MCP_CURRENT)
        self.assertEqual(negotiate_mcp_version([MCP_COMPATIBILITY]), MCP_COMPATIBILITY)
        with self.assertRaises(ProtocolHelperError) as caught:
            negotiate_mcp_version(["2025-06-18"])
        self.assertEqual(caught.exception.code, "UNSUPPORTED_PROTOCOL_VERSION")
        with self.assertRaises(ProtocolHelperError) as caught:
            negotiate_mcp_version([MCP_CURRENT, None])
        self.assertEqual(caught.exception.code, "UNSUPPORTED_PROTOCOL_VERSION")

    def test_all_mcp_task_states_match_golden_classification(self) -> None:
        actual = {state: classify_mcp_task_state(state) for state in VECTORS["mcpTaskStates"]}
        self.assertEqual(actual, VECTORS["mcpTaskStates"])

    def test_all_a2a_v1_task_states_match_golden_classification(self) -> None:
        actual = {state: classify_a2a_task_state(state) for state in VECTORS["a2aTaskStates"]}
        self.assertEqual(actual, VECTORS["a2aTaskStates"])

    def test_sse_cursor_is_opaque_and_preserved(self) -> None:
        vector = VECTORS["sse"]
        self.assertEqual(build_sse_resume_headers(vector["cursor"]), vector["expected"])

    def test_harness_cloud_event_matches_golden_bytes(self) -> None:
        event = VECTORS["cloudEvent"]["input"]
        self.assertEqual(validate_harness_cloud_event(event), event)
        self.assertEqual(
            serialize_harness_cloud_event(event).decode("utf-8"),
            VECTORS["cloudEvent"]["canonicalJson"],
        )

    def test_cloud_event_helper_tracks_the_pinned_contract_shape(self) -> None:
        schema = json.loads(
            (
                ROOT
                / "generators"
                / "contract-snapshot"
                / "schemas"
                / "v1alpha1"
                / "events"
                / "harness-cloud-event.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(set(schema["required"]), set(VECTORS["cloudEvent"]["input"]))
        self.assertEqual(
            set(schema["properties"]["data"]["required"]),
            set(VECTORS["cloudEvent"]["input"]["data"]),
        )
        self.assertIn(VECTORS["cloudEvent"]["input"]["type"], schema["properties"]["type"]["enum"])

    def test_mcp_denials_have_closed_reason_codes(self) -> None:
        current = copy.deepcopy(VECTORS["mcp"]["current"]["input"])
        compatibility = copy.deepcopy(VECTORS["mcp"]["compatibility"]["input"])
        cases = [
            ({**current, "version": "2025-06-18"}, "UNSUPPORTED_PROTOCOL_VERSION"),
            ({**current, "method": "roots/list"}, "DEPRECATED_MCP_METHOD"),
            ({**current, "method": "initialize"}, "LEGACY_HANDSHAKE_FORBIDDEN"),
            ({**current, "sessionId": "unexpected"}, "MCP_SESSION_FORBIDDEN"),
            ({key: value for key, value in compatibility.items() if key != "sessionId"}, "LEGACY_SESSION_REQUIRED"),
        ]
        for raw, reason in cases:
            with self.subTest(reason=reason), self.assertRaises(ProtocolHelperError) as caught:
                mcp_request(raw)
            self.assertEqual(caught.exception.code, reason)

    def test_invalid_task_and_resume_values_fail_closed(self) -> None:
        for function, value, reason in (
            (classify_mcp_task_state, "submitted", "INVALID_MCP_TASK_STATE"),
            (classify_a2a_task_state, "TASK_STATE_UNSPECIFIED", "INVALID_A2A_TASK_STATE"),
            (build_sse_resume_headers, "event\nnext", "UNSAFE_RESUME_CURSOR"),
        ):
            with self.subTest(reason=reason), self.assertRaises(ProtocolHelperError) as caught:
                function(value)
            self.assertEqual(caught.exception.code, reason)

    def test_malformed_cloud_events_fail_closed(self) -> None:
        unknown = copy.deepcopy(VECTORS["cloudEvent"]["input"])
        unknown["extension"] = "forbidden"
        mismatched = copy.deepcopy(VECTORS["cloudEvent"]["input"])
        mismatched["data"]["aggregateKind"] = "EvidenceRecord"
        duplicate = copy.deepcopy(VECTORS["cloudEvent"]["input"])
        duplicate["data"]["evidenceRefs"] = [
            duplicate["data"]["resourceRefs"][0], duplicate["data"]["resourceRefs"][0]
        ]
        for event in (unknown, mismatched, duplicate):
            with self.assertRaises(ProtocolHelperError) as caught:
                validate_harness_cloud_event(event)
            self.assertEqual(caught.exception.code, "MALFORMED_CLOUD_EVENT")


if __name__ == "__main__":
    unittest.main()
