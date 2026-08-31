"""Dependency-free deterministic PEP 517 backend for the generated Python SDK."""

from __future__ import annotations

import base64
import csv
import gzip
import hashlib
import io
import os
import tarfile
import zipfile
from pathlib import Path
from typing import Any, Iterable


NAME = "planeon-harness-sdk"
NORMALIZED_NAME = "planeon_harness_sdk"
VERSION = "0.1.0"
DIST_INFO = f"{NORMALIZED_NAME}-{VERSION}.dist-info"
ARCHIVE_ROOT = f"{NAME}-{VERSION}"
FIXED_EPOCH = 946684800
PYTHON_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PYTHON_ROOT.parent
PACKAGE_ROOT = PYTHON_ROOT / "src" / "planeon_harness"


def _metadata() -> bytes:
    return (
        "Metadata-Version: 2.4\n"
        f"Name: {NAME}\n"
        f"Version: {VERSION}\n"
        "Summary: Generated transport-neutral clients for Planeon MAS harness contracts\n"
        "License-Expression: Apache-2.0\n"
        "Requires-Python: >=3.10\n"
        "Description-Content-Type: text/markdown\n"
        "\n"
        "Offline-first generated Planeon harness SDK.\n"
    ).encode("utf-8")


def _wheel_metadata() -> bytes:
    return (
        "Wheel-Version: 1.0\n"
        "Generator: planeon-harness-sdk dependency-free-backend 1\n"
        "Root-Is-Purelib: true\n"
        "Tag: py3-none-any\n"
    ).encode("utf-8")


def _epoch() -> int:
    try:
        return max(int(os.environ.get("SOURCE_DATE_EPOCH", str(FIXED_EPOCH))), 315532800)
    except ValueError as exc:
        raise ValueError("SOURCE_DATE_EPOCH must be an integer") from exc


def _package_files() -> list[tuple[str, bytes]]:
    files: list[tuple[str, bytes]] = []
    for path in sorted(PACKAGE_ROOT.rglob("*"), key=lambda item: item.relative_to(PACKAGE_ROOT).as_posix()):
        if path.is_symlink():
            raise ValueError(f"linked package file is forbidden: {path}")
        if path.is_file() and not path.name.endswith((".pyc", ".pyo")):
            files.append(
                (
                    f"planeon_harness/{path.relative_to(PACKAGE_ROOT).as_posix()}",
                    path.read_bytes(),
                )
            )
    if not files:
        raise ValueError("generated Python package is empty")
    return files


def _record_digest(data: bytes) -> str:
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")
    return f"sha256={digest}"


def _record(files: Iterable[tuple[str, bytes]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    for name, data in files:
        writer.writerow((name, _record_digest(data), len(data)))
    writer.writerow((f"{DIST_INFO}/RECORD", "", ""))
    return stream.getvalue().encode("utf-8")


def _zip_info(name: str, epoch: int) -> zipfile.ZipInfo:
    import time

    info = zipfile.ZipInfo(name, time.gmtime(epoch)[:6])
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def get_requires_for_build_wheel(config_settings: dict[str, Any] | None = None) -> list[str]:
    del config_settings
    return []


def get_requires_for_build_sdist(config_settings: dict[str, Any] | None = None) -> list[str]:
    del config_settings
    return []


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    del config_settings, metadata_directory
    destination = Path(wheel_directory)
    destination.mkdir(parents=True, exist_ok=True)
    filename = f"{NORMALIZED_NAME}-{VERSION}-py3-none-any.whl"
    files = _package_files()
    files.extend(
        [
            (f"{DIST_INFO}/METADATA", _metadata()),
            (f"{DIST_INFO}/WHEEL", _wheel_metadata()),
            (f"{DIST_INFO}/licenses/LICENSE", (REPOSITORY_ROOT / "LICENSE").read_bytes()),
        ]
    )
    files.sort(key=lambda item: item[0])
    files.append((f"{DIST_INFO}/RECORD", _record(files)))
    with zipfile.ZipFile(destination / filename, "w", strict_timestamps=True) as archive:
        for name, data in files:
            archive.writestr(
                _zip_info(name, _epoch()),
                data,
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )
    return filename


def _tar_info(name: str, data: bytes) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = 0o644
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = _epoch()
    return info


def build_sdist(
    sdist_directory: str,
    config_settings: dict[str, Any] | None = None,
) -> str:
    del config_settings
    destination = Path(sdist_directory)
    destination.mkdir(parents=True, exist_ok=True)
    filename = f"{NAME}-{VERSION}.tar.gz"
    entries: list[tuple[str, bytes]] = [
        (f"{ARCHIVE_ROOT}/PKG-INFO", _metadata()),
        (f"{ARCHIVE_ROOT}/LICENSE", (REPOSITORY_ROOT / "LICENSE").read_bytes()),
        (f"{ARCHIVE_ROOT}/README.md", (REPOSITORY_ROOT / "README.md").read_bytes()),
        (f"{ARCHIVE_ROOT}/pyproject.toml", (PYTHON_ROOT / "pyproject.toml").read_bytes()),
        (f"{ARCHIVE_ROOT}/build_backend.py", Path(__file__).read_bytes()),
    ]
    entries.extend((f"{ARCHIVE_ROOT}/src/{name}", data) for name, data in _package_files())
    with (destination / filename).open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=_epoch(), compresslevel=9) as stream:
            with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as archive:
                for name, data in sorted(entries, key=lambda item: item[0]):
                    archive.addfile(_tar_info(name, data), io.BytesIO(data))
    return filename
