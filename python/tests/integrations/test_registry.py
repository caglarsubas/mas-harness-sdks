from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "python" / "src"))

from planeon_harness.integrations import (  # noqa: E402
    INTEGRATION_SPECS,
    IntegrationUnavailableError,
)
from planeon_harness.integrations import _base  # noqa: E402
from planeon_harness.integrations.crewai import instrument_crewai  # noqa: E402
from planeon_harness.integrations.langchain import instrument_langchain_runnable  # noqa: E402
from planeon_harness.integrations.langgraph import instrument_langgraph  # noqa: E402
from planeon_harness.integrations.mcp import instrument_mcp_client  # noqa: E402
from planeon_harness.integrations.semantic_kernel import (  # noqa: E402
    instrument_semantic_kernel,
)


class IntegrationRegistryTests(unittest.TestCase):
    def test_registry_is_immutable_and_matches_the_lock(self) -> None:
        self.assertIsInstance(INTEGRATION_SPECS, MappingProxyType)
        with self.assertRaises(TypeError):
            INTEGRATION_SPECS["extra"] = object()  # type: ignore[index]

        lock = json.loads(
            (ROOT / "python" / "optional-dependencies.lock").read_text(encoding="utf-8")
        )
        self.assertEqual(lock["schemaVersion"], "harness.planeon.ai/optional-dependencies-lock/v1alpha1")
        self.assertFalse(lock["networkRequired"])
        expected = {
            item["integration"]: {
                "baselineVersion": item["baselineVersion"],
                "distribution": item["distribution"],
                "extra": item["extra"],
                "importName": item["importName"],
                "requirement": item["requirement"],
                "sourceUrl": item["sourceUrl"],
                "verification": item["verification"],
            }
            for item in lock["integrations"]
        }
        actual = {
            name: {
                "baselineVersion": spec.baseline_version,
                "distribution": spec.distribution,
                "extra": spec.extra,
                "importName": spec.import_name,
                "requirement": spec.requirement,
                "sourceUrl": spec.source_url,
                "verification": spec.verification,
            }
            for name, spec in INTEGRATION_SPECS.items()
        }
        self.assertEqual(actual, expected)
        self.assertEqual(
            set(actual),
            {"crewai", "langchain", "langgraph", "mcp", "semantic_kernel"},
        )

    def test_base_import_does_not_attempt_optional_framework_imports(self) -> None:
        source = r'''
import sys

blocked = {"crewai", "langchain_core", "langgraph", "mcp", "semantic_kernel"}

class Blocker:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] in blocked:
            raise AssertionError(f"optional import attempted: {fullname}")
        return None

sys.meta_path.insert(0, Blocker())
import planeon_harness
import planeon_harness.integrations
assert blocked.isdisjoint(sys.modules)
'''
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(ROOT / "python" / "src"),
        }
        result = subprocess.run(
            [sys.executable, "-c", source],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_each_framework_factory_fails_with_its_exact_extra(self) -> None:
        factories = {
            "crewai": instrument_crewai,
            "langchain": instrument_langchain_runnable,
            "langgraph": instrument_langgraph,
            "mcp": instrument_mcp_client,
            "semantic_kernel": instrument_semantic_kernel,
        }
        with patch.object(
            _base.importlib,
            "import_module",
            side_effect=ModuleNotFoundError("framework denied"),
        ):
            for name, factory in factories.items():
                with self.subTest(name=name), self.assertRaises(IntegrationUnavailableError) as caught:
                    factory(object())
                self.assertEqual(caught.exception.code, "OPTIONAL_INTEGRATION_UNAVAILABLE")
                self.assertEqual(caught.exception.integration, name)
                self.assertEqual(caught.exception.extra, INTEGRATION_SPECS[name].extra)


if __name__ == "__main__":
    unittest.main()
