#!/usr/bin/env python3
"""Materialize a canonical public-contract snapshot and its immutable lock."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from common import (
    LOCK_PATH,
    LOCK_SCHEMA_VERSION,
    ROOT,
    SNAPSHOT_ROOT,
    canonical_json_bytes,
    load_json,
    safe_relative_path,
    sha256_bytes,
    sha256_file,
)


SOURCE_REPOSITORY = "https://github.com/caglarsubas/mas-harness-contracts.git"
SELECTED_PREFIXES = ("asyncapi/", "openapi/", "schemas/v1alpha1/")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _source_head(source_root: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
        shell=False,
    )
    if completed.returncode != 0:
        raise ValueError("contract source is not a readable Git checkout")
    return completed.stdout.strip()


def sync(source_root: Path, expected_commit: str) -> dict[str, object]:
    source_root = source_root.resolve()
    if COMMIT_PATTERN.fullmatch(expected_commit) is None:
        raise ValueError("expected contract commit must be a lower-case SHA-1")
    if _source_head(source_root) != expected_commit:
        raise ValueError("contract checkout does not match the approved commit")
    manifest_path = source_root / "contracts" / "release-manifest.json"
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("apiVersion") != "harness.planeon.ai/v1alpha1":
        raise ValueError("contract release manifest has an unknown authority")
    if manifest.get("extensionPacketIds") != ["CON-007"]:
        raise ValueError("contract release does not contain the approved CON-007 extension")
    raw_entries = manifest.get("entries")
    if not isinstance(raw_entries, list):
        raise ValueError("contract release manifest entries are absent")
    selected: list[dict[str, str]] = []
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict):
            raise ValueError("contract release manifest entry must be an object")
        source_path = raw_entry.get("path")
        if not isinstance(source_path, str) or not source_path.startswith(SELECTED_PREFIXES):
            continue
        relative = safe_relative_path(source_path)
        source = source_root / relative
        document = load_json(source)
        canonical = canonical_json_bytes(document)
        digest = sha256_bytes(canonical)
        if digest != raw_entry.get("sha256"):
            raise ValueError(f"release digest mismatch: {source_path}")
        destination = SNAPSHOT_ROOT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(canonical)
        selected.append(
            {
                "path": source_path,
                "sha256": digest,
                "role": str(raw_entry.get("role")),
            }
        )
    selected.sort(key=lambda entry: entry["path"])
    if len(selected) != 37:
        raise ValueError(f"expected 37 released API inputs, found {len(selected)}")

    canonical_manifest = canonical_json_bytes(manifest)
    snapshot_manifest = SNAPSHOT_ROOT / "contracts" / "release-manifest.json"
    snapshot_manifest.parent.mkdir(parents=True, exist_ok=True)
    snapshot_manifest.write_bytes(canonical_manifest)
    expected_files = {entry["path"] for entry in selected}
    expected_files.add("contracts/release-manifest.json")
    for path in sorted(SNAPSHOT_ROOT.rglob("*"), reverse=True):
        if path.is_symlink():
            raise ValueError(f"snapshot link is forbidden: {path.relative_to(SNAPSHOT_ROOT)}")
        if path.is_file() and path.relative_to(SNAPSHOT_ROOT).as_posix() not in expected_files:
            path.unlink()
        elif path.is_dir() and not any(path.iterdir()):
            path.rmdir()

    lock = {
        "schemaVersion": LOCK_SCHEMA_VERSION,
        "repository": SOURCE_REPOSITORY,
        "gitCommit": expected_commit,
        "release": {
            "packetId": manifest.get("packetId"),
            "version": manifest.get("releaseVersion"),
            "apiVersion": manifest.get("apiVersion"),
            "manifestPath": "contracts/release-manifest.json",
            "manifestSha256": sha256_bytes(canonical_manifest),
            "artifactState": manifest.get("artifactState"),
            "extensionPacketIds": manifest.get("extensionPacketIds"),
        },
        "snapshotRoot": "generators/contract-snapshot",
        "canonicalization": "SORTED_UTF8_JSON_V1",
        "files": selected,
    }
    LOCK_PATH.write_bytes(canonical_json_bytes(lock))
    return {
        "accepted": True,
        "files": len(selected),
        "gitCommit": expected_commit,
        "lockSha256": sha256_file(LOCK_PATH),
        "manifestSha256": sha256_bytes(canonical_manifest),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    arguments = parser.parse_args(argv)
    try:
        report = sync(arguments.source_root, arguments.commit)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"contract snapshot refused: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
