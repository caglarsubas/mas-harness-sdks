#!/usr/bin/env python3
"""Verify the SDK-001 preinstalled toolchain and dependency-free locks."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _load_lock(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"toolchain lock is absent or linked: {path.relative_to(ROOT)}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"toolchain lock must be an object: {path.relative_to(ROOT)}")
    return value


def prefetch() -> dict[str, object]:
    if os.environ.get("HARNESS_OFFLINE_ENFORCED") != "1":
        raise ValueError("prefetch requires the trusted offline process tree")
    if sys.version_info[:3] != (3, 12, 14):
        raise ValueError(f"SDK-001 requires Python 3.12.14, found {sys.version.split()[0]}")
    completed = subprocess.run(
        ["uv", "--version"],
        check=False,
        capture_output=True,
        text=True,
        shell=False,
    )
    version_parts = completed.stdout.split()
    if completed.returncode != 0 or version_parts[:2] != ["uv", "0.12.7"]:
        raise ValueError("SDK-001 requires the preinstalled pinned uv 0.12.7 executable")
    python_lock = _load_lock(ROOT / "python" / "toolchain.lock.json")
    typescript_lock = _load_lock(ROOT / "typescript" / "toolchain.lock.json")
    if python_lock != {
        "schemaVersion": "harness.planeon.ai/sdk-toolchain-lock/v1",
        "language": "python",
        "runtime": "CPython",
        "version": "3.12.14",
        "uvVersion": "0.12.7",
        "buildBackend": "dependency-free-stdlib-v1",
        "dependencies": [],
    }:
        raise ValueError("Python toolchain lock differs from SDK-001 authority")
    if typescript_lock != {
        "schemaVersion": "harness.planeon.ai/sdk-toolchain-lock/v1",
        "language": "typescript",
        "syntaxLevel": "5.x-erasable",
        "module": "ES2022",
        "generatorRuntime": "CPython-3.12.14",
        "generatorVersion": "planeon-contract-generator-v1",
        "compilerRequiredForGeneration": False,
        "dependencies": [],
    }:
        raise ValueError("TypeScript toolchain lock differs from SDK-001 authority")
    return {
        "accepted": True,
        "phase": "prefetch-local-cache-only",
        "python": sys.version.split()[0],
        "uv": "0.12.7",
        "pythonDependencies": 0,
        "typescriptDependencies": 0,
        "runtimeDownloads": False,
        "pythonLockSha256": _sha256(ROOT / "python" / "toolchain.lock.json"),
        "typescriptLockSha256": _sha256(ROOT / "typescript" / "toolchain.lock.json"),
    }


def main(argv: Sequence[str] | None = None) -> int:
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    if arguments == ("help",):
        print("Available targets: prefetch generated-check build-reproducible")
        print("All targets use closed packet-owned direct-argv descriptors.")
        return 0
    if arguments != ("prefetch",):
        print("usage: sdk_bootstrap.py {help|prefetch}", file=sys.stderr)
        return 2
    try:
        report = prefetch()
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"SDK bootstrap refused: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
