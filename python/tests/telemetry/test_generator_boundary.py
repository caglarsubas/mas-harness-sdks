from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT / "generators"))

import generate  # noqa: E402


class GeneratorBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_root = generate.ROOT
        self._temporary = tempfile.TemporaryDirectory(prefix="sdk-002-generator-boundary-")
        generate.ROOT = Path(self._temporary.name)
        self.generated_paths = (
            generate.ROOT / "typescript" / "src" / "models.ts",
            generate.ROOT / "typescript" / "dist" / "models.js",
        )
        self.extension_paths = (
            generate.ROOT / "typescript" / "src" / "telemetry" / "context.ts",
            generate.ROOT / "typescript" / "dist" / "telemetry" / "index.js",
        )
        for path in (*self.generated_paths, *self.extension_paths):
            path.parent.mkdir(parents=True, exist_ok=True)
        for path in self.generated_paths:
            path.write_bytes(b"generated\n")
        for path in self.extension_paths:
            path.write_bytes(b"packet-owned\n")
        self.outputs = {
            Path("typescript/src/models.ts"): b"generated\n",
            Path("typescript/dist/models.js"): b"generated\n",
        }

    def tearDown(self) -> None:
        generate.ROOT = self._original_root
        self._temporary.cleanup()

    def test_check_admits_packet_owned_subdirectory(self) -> None:
        generate._check(self.outputs)

    def test_write_preserves_packet_owned_subdirectory(self) -> None:
        for path in self.generated_paths:
            path.write_bytes(b"stale\n")
        generate._write(self.outputs)
        for path in self.generated_paths:
            self.assertEqual(path.read_bytes(), b"generated\n")
        for path in self.extension_paths:
            self.assertEqual(path.read_bytes(), b"packet-owned\n")

    def test_check_rejects_undeclared_top_level_source(self) -> None:
        for generated_path in self.generated_paths:
            extra = generated_path.parent / f"undeclared{generated_path.suffix}"
            extra.write_bytes(b"not-authorized\n")
            with self.assertRaisesRegex(ValueError, "undeclared output"):
                generate._check(self.outputs)
            extra.unlink()

    def test_check_rejects_linked_extension_path(self) -> None:
        for extension_path in self.extension_paths:
            linked = extension_path.with_name(f"linked{extension_path.suffix}")
            try:
                linked.symlink_to(extension_path)
            except OSError as exc:
                self.skipTest(f"symbolic links unavailable: {exc}")
            with self.assertRaisesRegex(ValueError, "linked output"):
                generate._check(self.outputs)
            linked.unlink()


if __name__ == "__main__":
    unittest.main()
