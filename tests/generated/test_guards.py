from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ci"))
sys.path.insert(0, str(ROOT / "generators"))

import validate_porting  # noqa: E402
import zero_bill_scan  # noqa: E402
from common import safe_relative_path  # noqa: E402


class GuardTests(unittest.TestCase):
    def test_repository_porting_ledger_is_inert(self) -> None:
        validate_porting.validate_inert_ledger(ROOT / "PORTING.yaml")

    def test_porting_copy_claim_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sdk-001-porting-") as directory:
            path = Path(directory) / "PORTING.yaml"
            path.write_text(
                "schemaVersion: harness.planeon.ai/porting-record/v1alpha1\n"
                "destinationRepository: mas-harness-sdks\n"
                "records: [COPY_AUTHORIZED]\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "NO_AUTHORIZATION"):
                validate_porting.validate_inert_ledger(path)

    def test_contract_snapshot_path_escape_is_rejected(self) -> None:
        for value in ("../secret.json", "/absolute.json", "windows\\path.json", ""):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    safe_relative_path(value)

    def test_repository_zero_bill_scan_passes(self) -> None:
        self.assertEqual(zero_bill_scan.scan(ROOT), [])

    def test_zero_bill_negative_workflow_fixture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sdk-001-zero-bill-") as directory:
            root = Path(directory)
            workflow = root / ".github" / "workflows" / "verify.yml"
            workflow.parent.mkdir(parents=True)
            workflow.write_text(
                "permissions:\n  contents: read\n"
                "jobs:\n  verify:\n    runs-on: ubuntu-latest\n"
                "    steps:\n      - uses: actions/cache@v4\n",
                encoding="utf-8",
            )
            python_manifest = root / "python" / "pyproject.toml"
            python_manifest.parent.mkdir()
            python_manifest.write_text("[project]\ndependencies = []\n", encoding="utf-8")
            typescript_manifest = root / "typescript" / "package.json"
            typescript_manifest.parent.mkdir()
            typescript_manifest.write_text(
                '{"dependencies":{},"devDependencies":{}}', encoding="utf-8"
            )
            violations = zero_bill_scan.scan(root)
            self.assertTrue(any("ubuntu-latest" in item for item in violations))
            self.assertTrue(any("actions/cache" in item for item in violations))


if __name__ == "__main__":
    unittest.main()
