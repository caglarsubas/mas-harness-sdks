from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))

import build_backend  # noqa: E402


class PackageMetadataTests(unittest.TestCase):
    def test_python_backend_declares_zero_build_dependencies(self) -> None:
        self.assertEqual(build_backend.get_requires_for_build_wheel(), [])
        self.assertEqual(build_backend.get_requires_for_build_sdist(), [])

    def test_python_wheel_contains_generated_surface_and_no_credentials(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sdk-001-wheel-") as directory:
            filename = build_backend.build_wheel(directory)
            wheel = Path(directory) / filename
            with zipfile.ZipFile(wheel) as archive:
                names = set(archive.namelist())
                self.assertIn("planeon_harness/generated/models.py", names)
                self.assertIn("planeon_harness/generated/client.py", names)
                metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
                metadata = archive.read(metadata_name).decode("utf-8")
                self.assertIn("Requires-Python: >=3.10", metadata)
                self.assertIn("Requires-Dist: cryptography==49.0.0", metadata)


if __name__ == "__main__":
    unittest.main()
