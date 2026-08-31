#!/usr/bin/env python3
"""Build Python and TypeScript packages twice and require byte identity."""

from __future__ import annotations

import gzip
import io
import json
import os
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

from common import ROOT, load_json, sha256_file
from generate import _check, expected_outputs


FIXED_EPOCH = 946684800
PYTHON_DIST = ROOT / "python" / "dist"
TYPESCRIPT_PACKAGE = ROOT / "typescript" / "package"


def _tar_info(name: str, data: bytes) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = 0o644
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = FIXED_EPOCH
    return info


def _typescript_archive(destination: Path) -> Path:
    package = load_json(ROOT / "typescript" / "package.json")
    if not isinstance(package, dict) or package.get("name") != "@planeon/harness-sdk":
        raise ValueError("TypeScript package manifest identity is invalid")
    if package.get("dependencies") != {} or package.get("devDependencies") != {}:
        raise ValueError("SDK-001 TypeScript package must have zero dependencies")
    entries = [
        ("package/package.json", (ROOT / "typescript" / "package.json").read_bytes()),
        ("package/LICENSE", (ROOT / "LICENSE").read_bytes()),
        ("package/README.md", (ROOT / "README.md").read_bytes()),
    ]
    dist_root = ROOT / "typescript" / "dist"
    for path in sorted(dist_root.rglob("*"), key=lambda item: item.relative_to(dist_root).as_posix()):
        if path.is_symlink():
            raise ValueError(f"linked TypeScript package file is forbidden: {path}")
        if path.is_file():
            entries.append((f"package/dist/{path.relative_to(dist_root).as_posix()}", path.read_bytes()))
    archive_path = destination / "planeon-harness-sdk-0.1.0.tgz"
    with archive_path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=FIXED_EPOCH, compresslevel=9) as stream:
            with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as archive:
                for name, data in sorted(entries, key=lambda item: item[0]):
                    archive.addfile(_tar_info(name, data), io.BytesIO(data))
    return archive_path


def _python_archives(destination: Path) -> tuple[Path, Path]:
    python_root = ROOT / "python"
    sys.path.insert(0, str(python_root))
    try:
        import build_backend

        wheel = destination / build_backend.build_wheel(str(destination))
        sdist = destination / build_backend.build_sdist(str(destination))
    finally:
        sys.path.remove(str(python_root))
    return wheel, sdist


def _one_build(root: Path) -> dict[str, Path]:
    python_root = root / "python"
    typescript_root = root / "typescript"
    python_root.mkdir(parents=True)
    typescript_root.mkdir(parents=True)
    wheel, sdist = _python_archives(python_root)
    typescript = _typescript_archive(typescript_root)
    return {"pythonWheel": wheel, "pythonSdist": sdist, "typescriptTgz": typescript}


def _replace_directory(destination: Path, sources: list[Path]) -> None:
    if destination.is_symlink():
        raise ValueError(f"artifact directory link is forbidden: {destination}")
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for source in sources:
        shutil.copy2(source, destination / source.name)


def build_reproducible() -> dict[str, object]:
    outputs = expected_outputs()
    _check(outputs)
    previous_epoch = os.environ.get("SOURCE_DATE_EPOCH")
    os.environ["SOURCE_DATE_EPOCH"] = str(FIXED_EPOCH)
    try:
        with tempfile.TemporaryDirectory(prefix="sdk-001-build-a-") as first_directory:
            with tempfile.TemporaryDirectory(prefix="sdk-001-build-b-") as second_directory:
                first = _one_build(Path(first_directory))
                second = _one_build(Path(second_directory))
                first_digests = {name: sha256_file(path) for name, path in first.items()}
                second_digests = {name: sha256_file(path) for name, path in second.items()}
                if first_digests != second_digests:
                    raise ValueError("two-build package digests differ")
                _replace_directory(
                    PYTHON_DIST,
                    [first["pythonWheel"], first["pythonSdist"]],
                )
                _replace_directory(TYPESCRIPT_PACKAGE, [first["typescriptTgz"]])
    finally:
        if previous_epoch is None:
            os.environ.pop("SOURCE_DATE_EPOCH", None)
        else:
            os.environ["SOURCE_DATE_EPOCH"] = previous_epoch
    return {
        "accepted": True,
        "buildsCompared": 2,
        "contractReleaseDigest": load_json(ROOT / "contracts.lock.json")["release"][
            "manifestSha256"
        ],
        "packages": first_digests,
        "published": False,
        "runtimeEvidence": False,
        "tenantAcceptance": False,
    }


def main() -> int:
    try:
        report = build_reproducible()
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"reproducible build refused: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
