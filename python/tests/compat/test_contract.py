from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "python" / "compat" / "prometa" / "src" / "prometa"

MAPPINGS = {
    "__init__.py": "planeon_harness",
    "guardrail.py": "planeon_harness.guardrail",
    "integrations.py": "planeon_harness.integrations",
    "protocols.py": "planeon_harness.protocols",
    "runtime.py": "planeon_harness.runtime",
}


class CompatibilitySourceContractTests(unittest.TestCase):
    def test_source_has_exactly_five_explicit_alias_modules(self) -> None:
        self.assertEqual(
            {path.name for path in PACKAGE.glob("*.py") if path.is_file()},
            set(MAPPINGS),
        )
        for filename, canonical in MAPPINGS.items():
            tree = ast.parse((PACKAGE / filename).read_text(encoding="utf-8"))
            imported_from = {
                node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
            }
            self.assertEqual(imported_from, {canonical})
            self.assertFalse(
                any(
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                    for node in ast.walk(tree)
                )
            )

    def test_compatibility_never_imports_private_canonical_modules(self) -> None:
        for path in PACKAGE.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("planeon_harness._", source)
            self.assertNotIn("._", source)


if __name__ == "__main__":
    unittest.main()
