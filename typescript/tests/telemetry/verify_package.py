#!/usr/bin/env python3
"""Verify the reproducible SDK archive carries the approved telemetry export."""

from __future__ import annotations

import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = ROOT / "typescript" / "package"
DIST_ROOT = ROOT / "typescript" / "dist" / "telemetry"
EXPECTED_EXPORT = {
    "types": "./dist/telemetry/index.d.ts",
    "import": "./dist/telemetry/index.js",
}
REQUIRED_MEMBERS = {
    "package/package.json",
    "package/dist/telemetry/index.js",
    "package/dist/telemetry/index.d.ts",
}


def _regular_bytes(path: Path) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"required package input is absent or linked: {path.relative_to(ROOT)}")
    return path.read_bytes()


def verify() -> dict[str, object]:
    archives = sorted(PACKAGE_ROOT.glob("*.tgz"))
    if len(archives) != 1 or archives[0].is_symlink():
        raise ValueError("exactly one regular TypeScript package archive is required")
    archive_path = archives[0]
    archive_bytes = _regular_bytes(archive_path)
    members: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
        for member in archive.getmembers():
            if member.name in members:
                raise ValueError(f"duplicate archive member is forbidden: {member.name}")
            if not member.isfile() or member.issym() or member.islnk():
                raise ValueError(f"non-regular archive member is forbidden: {member.name}")
            extracted = archive.extractfile(member)
            if extracted is None:
                raise ValueError(f"archive member could not be read: {member.name}")
            members[member.name] = extracted.read()
    missing = sorted(REQUIRED_MEMBERS - set(members))
    if missing:
        raise ValueError(f"telemetry package members are absent: {missing}")

    manifest = json.loads(members["package/package.json"])
    if manifest.get("exports", {}).get("./telemetry") != EXPECTED_EXPORT:
        raise ValueError("package telemetry export differs from SDK-002 authority")
    if manifest.get("dependencies") != {} or manifest.get("devDependencies") != {}:
        raise ValueError("packaged telemetry surface must remain dependency-free")
    for name, source in (
        ("package/dist/telemetry/index.js", DIST_ROOT / "index.js"),
        ("package/dist/telemetry/index.d.ts", DIST_ROOT / "index.d.ts"),
    ):
        if members[name] != _regular_bytes(source):
            raise ValueError(f"archive telemetry bytes differ from checked-in distribution: {name}")
    return {
        "accepted": True,
        "archive": archive_path.name,
        "archiveSha256": f"sha256:{hashlib.sha256(archive_bytes).hexdigest()}",
        "dependencies": 0,
        "packageExport": "./telemetry",
        "published": False,
        "telemetryMembers": sorted(REQUIRED_MEMBERS - {"package/package.json"}),
    }


def main() -> int:
    try:
        report = verify()
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError, tarfile.TarError) as exc:
        print(f"TypeScript telemetry package verification refused: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
