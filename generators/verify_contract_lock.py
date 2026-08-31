#!/usr/bin/env python3
"""Verify the closed SDK contract lock and canonical snapshot without Git."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from common import (
    LOCK_PATH,
    LOCK_SCHEMA_VERSION,
    SNAPSHOT_ROOT,
    load_json,
    safe_relative_path,
    sha256_file,
)


COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
LOCK_FIELDS = {
    "schemaVersion",
    "repository",
    "gitCommit",
    "release",
    "snapshotRoot",
    "canonicalization",
    "files",
}
RELEASE_FIELDS = {
    "packetId",
    "version",
    "apiVersion",
    "manifestPath",
    "manifestSha256",
    "artifactState",
    "extensionPacketIds",
}
FILE_FIELDS = {"path", "sha256", "role"}


def verify() -> dict[str, object]:
    lock = load_json(LOCK_PATH)
    if not isinstance(lock, dict) or set(lock) != LOCK_FIELDS:
        raise ValueError("contract lock fields are not closed")
    if lock["schemaVersion"] != LOCK_SCHEMA_VERSION:
        raise ValueError("contract lock schema is unknown")
    if lock["repository"] != "https://github.com/caglarsubas/mas-harness-contracts.git":
        raise ValueError("contract lock repository is not the public authority")
    commit = lock["gitCommit"]
    if not isinstance(commit, str) or COMMIT_PATTERN.fullmatch(commit) is None:
        raise ValueError("contract lock commit is invalid")
    if lock["snapshotRoot"] != "generators/contract-snapshot":
        raise ValueError("contract snapshot root differs from the closed location")
    if lock["canonicalization"] != "SORTED_UTF8_JSON_V1":
        raise ValueError("contract canonicalization is unknown")
    release = lock["release"]
    if not isinstance(release, dict) or set(release) != RELEASE_FIELDS:
        raise ValueError("contract release fields are not closed")
    if release != {
        "packetId": "CON-006",
        "version": "0.1.0",
        "apiVersion": "harness.planeon.ai/v1alpha1",
        "manifestPath": "contracts/release-manifest.json",
        "manifestSha256": release["manifestSha256"],
        "artifactState": "SOURCE_CONTRACT_ONLY",
        "extensionPacketIds": ["CON-007"],
    }:
        raise ValueError("contract release identity is not the approved source release")
    if not isinstance(release["manifestSha256"], str) or DIGEST_PATTERN.fullmatch(
        release["manifestSha256"]
    ) is None:
        raise ValueError("contract release manifest digest is invalid")
    manifest_path = SNAPSHOT_ROOT / safe_relative_path(release["manifestPath"])
    if sha256_file(manifest_path) != release["manifestSha256"]:
        raise ValueError("contract release manifest snapshot drifted")
    manifest = load_json(manifest_path)
    if (
        not isinstance(manifest, dict)
        or manifest.get("packetId") != release["packetId"]
        or manifest.get("extensionPacketIds") != release["extensionPacketIds"]
    ):
        raise ValueError("contract release manifest identity drifted")
    manifest_entries = {
        entry["path"]: entry
        for entry in manifest.get("entries", [])
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    }

    raw_files = lock["files"]
    if not isinstance(raw_files, list) or len(raw_files) != 37:
        raise ValueError("contract lock must contain exactly 37 API inputs")
    paths: list[str] = []
    roles: set[str] = set()
    for raw_entry in raw_files:
        if not isinstance(raw_entry, dict) or set(raw_entry) != FILE_FIELDS:
            raise ValueError("contract file lock fields are not closed")
        relative = safe_relative_path(raw_entry["path"])
        path = relative.as_posix()
        digest = raw_entry["sha256"]
        role = raw_entry["role"]
        if not isinstance(digest, str) or DIGEST_PATTERN.fullmatch(digest) is None:
            raise ValueError(f"contract file digest is invalid: {path}")
        if role not in {"PUBLIC_CONTRACT", "PREDECESSOR_CONTRACT"}:
            raise ValueError(f"contract file role is invalid: {path}")
        snapshot = SNAPSHOT_ROOT / relative
        if sha256_file(snapshot) != digest:
            raise ValueError(f"contract snapshot drifted: {path}")
        manifest_entry = manifest_entries.get(path)
        if manifest_entry is None or manifest_entry.get("sha256") != digest:
            raise ValueError(f"contract snapshot is absent from the release: {path}")
        if manifest_entry.get("role") != role:
            raise ValueError(f"contract release role drifted: {path}")
        paths.append(path)
        roles.add(role)
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ValueError("contract lock paths must be unique and sorted")

    actual = {
        path.relative_to(SNAPSHOT_ROOT).as_posix()
        for path in SNAPSHOT_ROOT.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    linked = [path for path in SNAPSHOT_ROOT.rglob("*") if path.is_symlink()]
    expected = set(paths) | {release["manifestPath"]}
    if linked or actual != expected:
        raise ValueError("contract snapshot contains linked, missing, or undeclared files")
    return {
        "accepted": True,
        "files": len(paths),
        "gitCommit": commit,
        "lockSha256": sha256_file(LOCK_PATH),
        "manifestSha256": release["manifestSha256"],
        "roles": sorted(roles),
    }


def main() -> int:
    try:
        report = verify()
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"contract lock refused: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
