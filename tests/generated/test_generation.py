from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "generators"))
sys.path.insert(0, str(ROOT / "python" / "src"))

import generate  # noqa: E402
import verify_contract_lock  # noqa: E402
from planeon_harness import CHANNELS, CONTRACT_RELEASE_DIGEST, HarnessClient  # noqa: E402
from planeon_harness.generated import MODEL_CONTRACTS, OPERATIONS, build_request  # noqa: E402


EXPECTED_OPERATIONS = {
    "getApprovalRequest",
    "getBundleRelease",
    "getEvidenceRecord",
    "getHarnessInstallation",
    "getOperation",
    "getOperatorOrganizationHarnessOverview",
    "getTenantHarnessOverview",
    "getTenantHarnessStatus",
    "getTenantPlaneStatus",
    "listOrganizationHarnessPortfolio",
    "recordApprovalDecision",
}
EXPECTED_CHANNELS = {
    "approvalStateChanged",
    "bundleReleaseStateChanged",
    "evidenceStateChanged",
    "installationStateChanged",
    "operationStateChanged",
    "policyBundleStateChanged",
    "statusProjectionUpdated",
}


class GenerationTests(unittest.TestCase):
    def test_contract_lock_and_snapshot_are_closed(self) -> None:
        report = verify_contract_lock.verify()
        self.assertTrue(report["accepted"])
        self.assertEqual(report["files"], 37)
        self.assertEqual(
            report["manifestSha256"],
            "sha256:c5dd4c39d1c69d07f8d8de3d1a09584bb906172fee2d5ac20ad25ff344b0db79",
        )

    def test_committed_generation_matches_expected_bytes(self) -> None:
        outputs = generate.expected_outputs()
        generate._check(outputs)
        self.assertEqual(len(outputs), 17)

    def test_golden_inventory_covers_every_api_and_event_channel(self) -> None:
        manifest = json.loads(
            (ROOT / "tests" / "generated" / "golden-manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual({item["operationId"] for item in manifest["operations"]}, EXPECTED_OPERATIONS)
        self.assertEqual(set(manifest["channels"]), EXPECTED_CHANNELS)
        self.assertEqual(manifest["messages"], ["HarnessCloudEvent"])
        self.assertEqual(len(manifest["models"]), 89)
        self.assertEqual(len(manifest["generatedFiles"]), 16)

    def test_python_surface_is_release_bound(self) -> None:
        self.assertEqual(
            CONTRACT_RELEASE_DIGEST,
            "sha256:c5dd4c39d1c69d07f8d8de3d1a09584bb906172fee2d5ac20ad25ff344b0db79",
        )
        self.assertEqual(len(MODEL_CONTRACTS), 89)
        self.assertEqual(set(OPERATIONS), EXPECTED_OPERATIONS)
        self.assertEqual(set(CHANNELS), EXPECTED_CHANNELS)

    def test_python_request_builder_encodes_paths_queries_headers_and_body(self) -> None:
        client = HarnessClient()
        request = client.get_operation(operation_id="operation/with space")
        self.assertEqual(request.method, "GET")
        self.assertEqual(request.path, "/api/v1alpha1/operations/operation%2Fwith%20space")
        self.assertEqual(request.query, ())
        self.assertEqual(request.headers, ())

        portfolio = client.list_organization_harness_portfolio(
            cursor="next", limit=25, state="READY"
        )
        self.assertEqual(
            portfolio.query,
            (("cursor", "next"), ("limit", "25"), ("state", "READY")),
        )

        decision = client.record_approval_decision(
            idempotency_key="idem-1",
            if_match='"etag-1"',
            approval_id="approval-1",
            body={"decision": "APPROVE"},
        )
        self.assertEqual(decision.method, "POST")
        self.assertEqual(decision.path, "/api/v1alpha1/approvals/approval-1/decision")
        self.assertEqual(
            decision.headers,
            (
                ("Idempotency-Key", "idem-1"),
                ("If-Match", '"etag-1"'),
                ("Content-Type", "application/json"),
            ),
        )

    def test_python_request_builder_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown operation"):
            build_request("notRegistered", {})
        with self.assertRaisesRegex(ValueError, "missing operation parameter"):
            build_request("getOperation", {})
        with self.assertRaisesRegex(ValueError, "unknown operation parameter"):
            build_request("getTenantHarnessOverview", {"tenant_id": "untrusted"})
        with self.assertRaisesRegex(ValueError, "request body is required"):
            build_request(
                "recordApprovalDecision",
                {
                    "idempotency_key": "idem-1",
                    "if_match": '"etag-1"',
                    "approval_id": "approval-1",
                },
            )

    def test_typescript_package_has_valid_declaration_shape_and_no_transport(self) -> None:
        declaration = (ROOT / "typescript" / "dist" / "client.d.ts").read_text(
            encoding="utf-8"
        )
        runtime = (ROOT / "typescript" / "dist" / "client.js").read_text(encoding="utf-8")
        source = (ROOT / "typescript" / "src" / "client.ts").read_text(encoding="utf-8")
        self.assertIn("export declare function recordApprovalDecision", declaration)
        self.assertNotIn("export function buildRequest(", declaration)
        self.assertNotIn("fetch(", runtime)
        self.assertNotIn("axios", source)
        package = json.loads((ROOT / "typescript" / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package["dependencies"], {})
        self.assertEqual(package["devDependencies"], {})
        self.assertEqual(
            package["exports"]["./runtime"],
            {
                "types": "./dist/runtime/index.d.ts",
                "import": "./dist/runtime/index.js",
            },
        )


if __name__ == "__main__":
    unittest.main()
