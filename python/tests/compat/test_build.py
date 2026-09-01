from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import tomllib
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = ROOT / "python" / "compat" / "prometa"
sys.path.insert(0, str(BACKEND_ROOT))

import build_compat  # noqa: E402


class CompatibilityBuildTests(unittest.TestCase):
    def test_manifest_and_backend_contract_are_closed(self) -> None:
        manifest = tomllib.loads(
            (ROOT / "python" / "compat-pyproject.toml").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest, build_compat.EXPECTED_MANIFEST)
        self.assertEqual(build_compat.get_requires_for_build_wheel(), [])
        self.assertFalse(hasattr(build_compat, "build_sdist"))
        self.assertEqual(
            manifest["project"]["dependencies"],
            ["planeon-harness-sdk==0.1.0"],
        )
        self.assertEqual(
            manifest["tool"]["planeon"]["compatibility"]["network-default"],
            "disabled",
        )

    def test_backend_rejects_manifest_semantic_drift(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sdk-007-manifest-drift-") as directory:
            drifted = Path(directory) / "compat-pyproject.toml"
            drifted.write_text(
                (ROOT / "python" / "compat-pyproject.toml")
                .read_text(encoding="utf-8")
                .replace("planeon-harness-sdk==0.1.0", "planeon-harness-sdk>=0.1.0"),
                encoding="utf-8",
            )
            with patch.object(build_compat, "MANIFEST_PATH", drifted):
                with self.assertRaisesRegex(ValueError, "differs from the closed"):
                    build_compat._validate_manifest()

    def test_wheel_members_metadata_modes_timestamps_and_record_are_closed(self) -> None:
        expected_members = {
            "prometa/__init__.py",
            "prometa/guardrail.py",
            "prometa/integrations.py",
            "prometa/protocols.py",
            "prometa/runtime.py",
            f"{build_compat.DIST_INFO}/METADATA",
            f"{build_compat.DIST_INFO}/WHEEL",
            f"{build_compat.DIST_INFO}/licenses/LICENSE",
            f"{build_compat.DIST_INFO}/RECORD",
        }
        with tempfile.TemporaryDirectory(prefix="sdk-007-closed-wheel-") as directory:
            wheel = Path(directory) / build_compat.build_wheel(directory)
            with zipfile.ZipFile(wheel) as archive:
                self.assertEqual(set(archive.namelist()), expected_members)
                self.assertEqual(archive.namelist(), sorted(archive.namelist()))
                for info in archive.infolist():
                    self.assertEqual(info.date_time, (2000, 1, 1, 0, 0, 0))
                    self.assertEqual((info.external_attr >> 16) & 0o777, 0o644)
                metadata = archive.read(f"{build_compat.DIST_INFO}/METADATA").decode()
                self.assertIn("Requires-Dist: planeon-harness-sdk==0.1.0\n", metadata)
                self.assertNotIn("Requires-Dist: prometa", metadata)
                wheel_metadata = archive.read(f"{build_compat.DIST_INFO}/WHEEL").decode()
                self.assertEqual(wheel_metadata.count("Tag: py3-none-any"), 1)
                record = archive.read(f"{build_compat.DIST_INFO}/RECORD").decode()
                rows = list(csv.reader(io.StringIO(record)))
                self.assertEqual({row[0] for row in rows}, set(archive.namelist()))
                for name, digest, size in rows[:-1]:
                    data = archive.read(name)
                    expected = (
                        base64.urlsafe_b64encode(hashlib.sha256(data).digest())
                        .rstrip(b"=")
                        .decode()
                    )
                    self.assertEqual(digest, f"sha256={expected}")
                    self.assertEqual(size, str(len(data)))
                self.assertEqual(rows[-1], [f"{build_compat.DIST_INFO}/RECORD", "", ""])

    def test_default_verifier_is_reproducible_and_retains_no_artifact(self) -> None:
        before = set(BACKEND_ROOT.rglob("*.whl")) | set(ROOT.glob("*.whl"))
        completed = subprocess.run(
            [sys.executable, str(BACKEND_ROOT / "build_compat.py"), "--verify-reproducible"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(
            set(report),
            {
                "accepted",
                "buildsCompared",
                "published",
                "runtimeEvidence",
                "tenantAcceptance",
                "wheelSha256",
            },
        )
        self.assertEqual(report["accepted"], True)
        self.assertEqual(report["buildsCompared"], 2)
        self.assertEqual(report["published"], False)
        self.assertEqual(report["runtimeEvidence"], False)
        self.assertEqual(report["tenantAcceptance"], False)
        self.assertRegex(report["wheelSha256"], r"^[0-9a-f]{64}$")
        after = set(BACKEND_ROOT.rglob("*.whl")) | set(ROOT.glob("*.whl"))
        self.assertEqual(after, before)

    def test_explicit_empty_output_receives_one_verified_wheel(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sdk-007-output-") as directory:
            report = build_compat.verify_reproducible(Path(directory))
            artifacts = list(Path(directory).iterdir())
            self.assertEqual([path.name for path in artifacts], [build_compat.WHEEL_FILENAME])
            self.assertEqual(
                hashlib.sha256(artifacts[0].read_bytes()).hexdigest(),
                report["wheelSha256"],
            )
            self.assertEqual(report["published"], False)


if __name__ == "__main__":
    unittest.main()
