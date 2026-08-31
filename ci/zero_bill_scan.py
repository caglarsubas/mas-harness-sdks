#!/usr/bin/env python3
"""Fail closed on hosted, metered, credentialed, or download-capable defaults."""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Iterable, Sequence


FORBIDDEN_WORKFLOW_TOKENS = {
    "actions/cache",
    "actions/upload-artifact",
    "schedule:",
    "ubuntu-latest",
    "windows-latest",
    "macos-latest",
    "ghcr.io",
}
FORBIDDEN_RUNTIME_PATTERNS = {
    "Python provider import": re.compile(
        r"^(?:from|import)\s+(?:aiohttp|boto3|google\.cloud|httpx|requests|urllib3)(?:\s|\.|$)",
        re.MULTILINE,
    ),
    "Python network import": re.compile(r"^(?:from|import)\s+urllib\.request(?:\s|\.|$)", re.MULTILINE),
    "TypeScript fetch": re.compile(r"\bfetch\s*\("),
    "TypeScript network client": re.compile(r"(?:from\s+['\"](?:axios|got|undici)['\"]|require\(['\"](?:axios|got|undici)['\"]\))"),
}
PINNED_ACTION = re.compile(r"^\s*uses:\s*([^@\s]+)@([0-9a-f]{40})\s*$", re.MULTILINE)
ANY_ACTION = re.compile(r"^\s*uses:\s*([^@\s]+)@([^\s]+)\s*$", re.MULTILINE)


def _files(root: Path, paths: Iterable[str]) -> Iterable[Path]:
    for relative in paths:
        path = root / relative
        if path.is_file() and not path.is_symlink():
            yield path
        elif path.is_dir() and not path.is_symlink():
            yield from sorted(
                (item for item in path.rglob("*") if item.is_file() and not item.is_symlink()),
                key=lambda item: item.as_posix(),
            )


def scan(root: Path) -> list[str]:
    violations: list[str] = []
    workflow = root / ".github" / "workflows" / "verify.yml"
    if not workflow.is_file() or workflow.is_symlink():
        return ["required workflow is absent or linked"]
    workflow_text = workflow.read_text(encoding="utf-8")
    folded = workflow_text.casefold()
    for token in sorted(FORBIDDEN_WORKFLOW_TOKENS):
        if token in folded:
            violations.append(f"workflow contains forbidden token: {token}")
    label = "runs-on: [self-hosted, harness-engineering, ephemeral, credential-free]"
    if workflow_text.count(label) != 1:
        violations.append("workflow must use the exact credential-free self-hosted labels")
    if "permissions:\n  contents: read" not in workflow_text:
        violations.append("workflow permissions must be contents-read only")
    if "persist-credentials: false" not in workflow_text:
        violations.append("checkout credentials must not persist")
    if workflow_text.count("run: /opt/planeon/bin/harness-offline-launch") != 1:
        violations.append("workflow must invoke exactly the trusted host launcher")
    if ANY_ACTION.findall(workflow_text) != PINNED_ACTION.findall(workflow_text):
        violations.append("every workflow action must be pinned by a 40-character commit")
    if any(action != "actions/checkout" for action, _digest in PINNED_ACTION.findall(workflow_text)):
        violations.append("the pinned checkout is the only admitted workflow action")

    for path in _files(
        root,
        (
            "python/src",
            "typescript/src",
            "typescript/dist",
            "generators",
            "ci",
        ),
    ):
        if path.suffix not in {".py", ".ts", ".js"} or path.name == "network_canary.py":
            continue
        text = path.read_text(encoding="utf-8")
        for name, pattern in FORBIDDEN_RUNTIME_PATTERNS.items():
            if pattern.search(text):
                violations.append(f"{name} is forbidden: {path.relative_to(root)}")

    python_manifest = tomllib.loads((root / "python" / "pyproject.toml").read_text(encoding="utf-8"))
    if python_manifest.get("project", {}).get("dependencies") != []:
        violations.append("Python core dependencies must remain empty in SDK-001")
    typescript_manifest = json.loads((root / "typescript" / "package.json").read_text(encoding="utf-8"))
    if typescript_manifest.get("dependencies") != {} or typescript_manifest.get("devDependencies") != {}:
        violations.append("TypeScript dependencies must remain empty in SDK-001")
    return sorted(set(violations))


def main(argv: Sequence[str] | None = None) -> int:
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 1:
        print("usage: zero_bill_scan.py REPOSITORY", file=sys.stderr)
        return 2
    try:
        violations = scan(Path(arguments[0]).resolve())
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"zero-bill scan refused: {exc}", file=sys.stderr)
        return 1
    report = {
        "externalTelemetry": False,
        "githubArtifactStorage": False,
        "hostedRunner": False,
        "paidProvider": False,
        "runtimeDownloads": False,
        "status": "FAIL" if violations else "PASS",
        "thirdPartyApiKey": False,
        "violations": violations,
    }
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
