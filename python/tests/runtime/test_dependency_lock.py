from __future__ import annotations

import importlib.metadata
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "python" / "src"))


class DependencyLockTests(unittest.TestCase):
    def test_cryptography_closure_is_exact_hash_pinned_and_offline(self) -> None:
        lock = json.loads((ROOT / "python" / "runtime-dependencies.lock.json").read_text())
        self.assertFalse(lock["networkRequired"])
        self.assertEqual(lock["source"], "PREPROVISIONED_OFFLINE_WHEELHOUSE")
        self.assertEqual(
            [(item["name"], item["version"]) for item in lock["packages"]],
            [("cffi", "2.1.0"), ("cryptography", "49.0.0"), ("pycparser", "3.0")],
        )
        for item in lock["packages"]:
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")

    def test_runtime_uses_the_packet_pinned_cryptography_distribution(self) -> None:
        self.assertEqual(importlib.metadata.version("cryptography"), "49.0.0")


if __name__ == "__main__":
    unittest.main()
