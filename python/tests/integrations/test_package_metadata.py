from __future__ import annotations

import json
import sys
import tarfile
import tempfile
import tomllib
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "python" / "src"))

import build_backend  # noqa: E402

from planeon_harness.integrations import INTEGRATION_SPECS  # noqa: E402


class OptionalMetadataTests(unittest.TestCase):
    def expected(self) -> dict[str, str]:
        return {spec.extra: spec.requirement for spec in INTEGRATION_SPECS.values()}

    def test_pyproject_builder_and_lock_are_exactly_aligned(self) -> None:
        manifest = tomllib.loads(
            (ROOT / "python" / "pyproject.toml").read_text(encoding="utf-8")
        )
        pyproject_extras = {
            extra: requirements[0]
            for extra, requirements in manifest["project"]["optional-dependencies"].items()
        }
        backend_extras = dict(build_backend.OPTIONAL_DEPENDENCIES)
        lock = json.loads(
            (ROOT / "python" / "optional-dependencies.lock").read_text(encoding="utf-8")
        )
        lock_extras = {item["extra"]: item["requirement"] for item in lock["integrations"]}
        self.assertEqual(pyproject_extras, self.expected())
        self.assertEqual(backend_extras, self.expected())
        self.assertEqual(lock_extras, self.expected())
        self.assertEqual(manifest["project"]["dependencies"], ["cryptography==49.0.0"])

    def test_wheel_metadata_contains_only_isolated_declared_extras(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sdk-005-wheel-") as directory:
            wheel = Path(directory) / build_backend.build_wheel(directory)
            with zipfile.ZipFile(wheel) as archive:
                metadata_name = next(
                    name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
                )
                metadata = archive.read(metadata_name).decode("utf-8")
        self.assertEqual(
            {
                line.removeprefix("Provides-Extra: ")
                for line in metadata.splitlines()
                if line.startswith("Provides-Extra: ")
            },
            set(self.expected()),
        )
        for extra, requirement in self.expected().items():
            self.assertIn(
                f'Requires-Dist: {requirement}; extra == "{extra}"',
                metadata,
            )
        for forbidden in ("openai", "anthropic", "google", "qdrant", "weaviate", "milvus"):
            self.assertNotIn(forbidden, metadata.casefold())

    def test_sdist_contains_the_public_compatibility_lock(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sdk-005-sdist-") as directory:
            sdist = Path(directory) / build_backend.build_sdist(directory)
            with tarfile.open(sdist, mode="r:gz") as archive:
                names = set(archive.getnames())
        self.assertIn(
            f"planeon-harness-sdk-{build_backend.VERSION}/optional-dependencies.lock",
            names,
        )


if __name__ == "__main__":
    unittest.main()
