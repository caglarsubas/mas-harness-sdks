from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CANONICAL_SOURCE = ROOT / "python" / "src"
BACKEND_ROOT = ROOT / "python" / "compat" / "prometa"
sys.path.insert(0, str(BACKEND_ROOT))

import build_compat  # noqa: E402


class CompatibilityAliasTests(unittest.TestCase):
    def build(self, directory: str) -> Path:
        return Path(directory) / build_compat.build_wheel(directory)

    def run_isolated(self, wheel: Path, program: str) -> subprocess.CompletedProcess[str]:
        environment = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
        }
        return subprocess.run(
            [sys.executable, "-B", "-I", "-c", program, str(wheel), str(CANONICAL_SOURCE)],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )

    def test_wheel_aliases_are_exact_identical_and_emit_one_warning(self) -> None:
        program = r'''
import importlib, json, sys, warnings
sys.path[:0] = [sys.argv[1], sys.argv[2]]
canonical_names = ["planeon_harness", "planeon_harness.guardrail", "planeon_harness.integrations", "planeon_harness.protocols", "planeon_harness.runtime"]
compat_names = ["prometa", "prometa.guardrail", "prometa.integrations", "prometa.protocols", "prometa.runtime"]
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    compatible = [importlib.import_module(name) for name in compat_names]
canonical = [importlib.import_module(name) for name in canonical_names]
for alias, target in zip(compatible, canonical):
    assert alias.__all__ == target.__all__
    assert all(getattr(alias, name) is getattr(target, name) for name in target.__all__)
assert compatible[0].__version__ == canonical[0].__version__ == "0.1.0"
assert len(caught) == 1
assert caught[0].category is DeprecationWarning
assert str(caught[0].message) == "The prometa import is deprecated; use planeon_harness. It is supported only through planeon-harness-sdk v1 and will be removed in v2."
for name in ("langchain", "langgraph", "crewai", "semantic_kernel", "mcp"):
    assert name not in sys.modules
assert not hasattr(compatible[0], "telemetry")
try:
    importlib.import_module("prometa.telemetry")
except ModuleNotFoundError:
    pass
else:
    raise AssertionError("unknown compatibility module resolved")
print(json.dumps({"accepted": True, "aliases": compat_names}, sort_keys=True))
'''
        with tempfile.TemporaryDirectory(prefix="sdk-007-alias-wheel-") as directory:
            completed = self.run_isolated(self.build(directory), program)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["accepted"], True)

    def test_canonical_sdk_imports_when_all_prometa_imports_are_blocked(self) -> None:
        program = r'''
import importlib, importlib.abc, json, sys
sys.path[:0] = [sys.argv[1], sys.argv[2]]
class BlockPrometa(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "prometa" or fullname.startswith("prometa."):
            raise AssertionError(f"canonical SDK attempted compatibility import: {fullname}")
        return None
sys.meta_path.insert(0, BlockPrometa())
names = ["planeon_harness", "planeon_harness.guardrail", "planeon_harness.integrations", "planeon_harness.protocols", "planeon_harness.runtime"]
for name in names:
    importlib.import_module(name)
assert not any(name == "prometa" or name.startswith("prometa.") for name in sys.modules)
print(json.dumps({"accepted": True, "canonical": names}, sort_keys=True))
'''
        with tempfile.TemporaryDirectory(prefix="sdk-007-direction-wheel-") as directory:
            completed = self.run_isolated(self.build(directory), program)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["accepted"], True)


if __name__ == "__main__":
    unittest.main()
