#!/usr/bin/env python3
"""Dependency-free deterministic wheel backend for planeon-prometa-compat."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import shutil
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path
from typing import Any, Iterable, Sequence


NAME = "planeon-prometa-compat"
NORMALIZED_NAME = "planeon_prometa_compat"
VERSION = "0.1.0"
DIST_INFO = f"{NORMALIZED_NAME}-{VERSION}.dist-info"
WHEEL_FILENAME = f"{NORMALIZED_NAME}-{VERSION}-py3-none-any.whl"
FIXED_EPOCH = 946684800
BACKEND_ROOT = Path(__file__).resolve().parent
PYTHON_ROOT = BACKEND_ROOT.parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parents[2]
MANIFEST_PATH = PYTHON_ROOT / "compat-pyproject.toml"
PACKAGE_ROOT = BACKEND_ROOT / "src" / "prometa"
PACKAGE_FILES = (
    "__init__.py",
    "guardrail.py",
    "integrations.py",
    "protocols.py",
    "runtime.py",
)
EXPECTED_MANIFEST: dict[str, object] = {
    "build-system": {
        "requires": [],
        "build-backend": "build_compat",
        "backend-path": ["compat/prometa"],
    },
    "project": {
        "name": NAME,
        "version": VERSION,
        "description": "Deprecated prometa import aliases for planeon-harness-sdk v1 migrations",
        "requires-python": ">=3.10",
        "license": "Apache-2.0",
        "dependencies": ["planeon-harness-sdk==0.1.0"],
    },
    "tool": {
        "planeon": {
            "compatibility": {
                "canonical-import": "planeon_harness",
                "compatibility-import": "prometa",
                "removal-version": "2.0.0",
                "network-default": "disabled",
            }
        }
    },
}


def _require_regular(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be a regular non-linked file: {path}")


def _validate_manifest() -> None:
    _require_regular(MANIFEST_PATH, "compatibility build manifest")
    try:
        manifest = tomllib.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ValueError("compatibility build manifest is invalid TOML") from exc
    if manifest != EXPECTED_MANIFEST:
        raise ValueError("compatibility build manifest differs from the closed SDK-007 contract")


def _package_files() -> list[tuple[str, bytes]]:
    if PACKAGE_ROOT.is_symlink() or not PACKAGE_ROOT.is_dir():
        raise ValueError("compatibility package root must be a regular directory")
    discovered = {
        path.relative_to(PACKAGE_ROOT).as_posix()
        for path in PACKAGE_ROOT.rglob("*.py")
        if path.is_file()
    }
    if discovered != set(PACKAGE_FILES):
        raise ValueError("compatibility package module inventory differs from SDK-007")
    files: list[tuple[str, bytes]] = []
    for relative in PACKAGE_FILES:
        path = PACKAGE_ROOT / relative
        _require_regular(path, "compatibility module")
        files.append((f"prometa/{relative}", path.read_bytes()))
    return files


def _metadata() -> bytes:
    return (
        "Metadata-Version: 2.4\n"
        f"Name: {NAME}\n"
        f"Version: {VERSION}\n"
        "Summary: Deprecated prometa import aliases for planeon-harness-sdk v1 migrations\n"
        "License-Expression: Apache-2.0\n"
        "Requires-Python: >=3.10\n"
        "Requires-Dist: planeon-harness-sdk==0.1.0\n"
        "Description-Content-Type: text/markdown\n"
        "\n"
        "Offline-only migration aliases for the canonical Planeon harness SDK.\n"
    ).encode("utf-8")


def _wheel_metadata() -> bytes:
    return (
        "Wheel-Version: 1.0\n"
        "Generator: planeon-prometa-compat dependency-free-backend 1\n"
        "Root-Is-Purelib: true\n"
        "Tag: py3-none-any\n"
    ).encode("utf-8")


def _record_digest(data: bytes) -> str:
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
    return f"sha256={digest.decode('ascii')}"


def _record(files: Iterable[tuple[str, bytes]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    for name, data in files:
        writer.writerow((name, _record_digest(data), len(data)))
    writer.writerow((f"{DIST_INFO}/RECORD", "", ""))
    return stream.getvalue().encode("utf-8")


def _zip_info(name: str) -> zipfile.ZipInfo:
    import time

    info = zipfile.ZipInfo(name, time.gmtime(FIXED_EPOCH)[:6])
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def get_requires_for_build_wheel(config_settings: dict[str, Any] | None = None) -> list[str]:
    del config_settings
    return []


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    del config_settings, metadata_directory
    _validate_manifest()
    destination = Path(wheel_directory)
    if destination.is_symlink() or not destination.is_dir():
        raise ValueError("wheel destination must be an existing non-linked directory")
    license_path = REPOSITORY_ROOT / "LICENSE"
    _require_regular(license_path, "repository license")
    files = _package_files()
    files.extend(
        (
            (f"{DIST_INFO}/METADATA", _metadata()),
            (f"{DIST_INFO}/WHEEL", _wheel_metadata()),
            (f"{DIST_INFO}/licenses/LICENSE", license_path.read_bytes()),
        )
    )
    files.sort(key=lambda item: item[0])
    files.append((f"{DIST_INFO}/RECORD", _record(files)))
    files.sort(key=lambda item: item[0])
    wheel = destination / WHEEL_FILENAME
    if wheel.exists() or wheel.is_symlink():
        raise ValueError("wheel destination already contains the SDK-007 artifact")
    with zipfile.ZipFile(wheel, "w", strict_timestamps=True) as archive:
        for name, data in files:
            archive.writestr(
                _zip_info(name),
                data,
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )
    return WHEEL_FILENAME


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_reproducible(output_directory: Path | None = None) -> dict[str, object]:
    if output_directory is not None and (
        output_directory.is_symlink() or not output_directory.is_dir()
    ):
        raise ValueError("explicit output must be an existing non-linked directory")
    with tempfile.TemporaryDirectory(prefix="sdk-007-build-a-") as first_directory:
        with tempfile.TemporaryDirectory(prefix="sdk-007-build-b-") as second_directory:
            first = Path(first_directory) / build_wheel(first_directory)
            second = Path(second_directory) / build_wheel(second_directory)
            first_digest = _sha256(first)
            if first_digest != _sha256(second) or first.read_bytes() != second.read_bytes():
                raise ValueError("two-build compatibility wheels differ")
            if output_directory is not None:
                output = output_directory / WHEEL_FILENAME
                if output.exists() or output.is_symlink():
                    raise ValueError("explicit output already contains the SDK-007 artifact")
                shutil.copyfile(first, output)
    return {
        "accepted": True,
        "buildsCompared": 2,
        "published": False,
        "runtimeEvidence": False,
        "tenantAcceptance": False,
        "wheelSha256": first_digest,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-reproducible", action="store_true", required=True)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        report = verify_reproducible(arguments.output)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"compatibility build refused: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
