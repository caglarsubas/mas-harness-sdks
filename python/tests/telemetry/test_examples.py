from __future__ import annotations

import runpy
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PYTHON_SRC = REPOSITORY_ROOT / "python" / "src"


class ExampleTests(unittest.TestCase):
    def test_python_example_runs_without_network_or_credentials(self) -> None:
        sys.path.insert(0, str(PYTHON_SRC))
        try:
            namespace = runpy.run_path(
                str(REPOSITORY_ROOT / "examples" / "telemetry" / "python_example.py")
            )
        finally:
            sys.path.remove(str(PYTHON_SRC))
        self.assertEqual(len(namespace["sink"].records), 1)


if __name__ == "__main__":
    unittest.main()
