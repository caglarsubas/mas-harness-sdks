"""Shared canonical-file helpers for the dependency-free SDK generators."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ROOT = ROOT / "generators" / "contract-snapshot"
LOCK_PATH = ROOT / "contracts.lock.json"
LOCK_SCHEMA_VERSION = "harness.planeon.ai/contract-release-lock/v1"


def canonical_json_bytes(value: Any) -> bytes:
    """Encode finite JSON in the contract repository's stable representation."""

    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8") + b"\n"


def sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return f"sha256:{digest.hexdigest()}"


def load_json(path: Path, *, regular: bool = True) -> Any:
    if regular and (not path.is_file() or path.is_symlink()):
        raise ValueError(f"required regular JSON file is absent: {path}")
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON number: {value}")
            ),
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError(f"invalid JSON file: {path}") from exc


def safe_relative_path(value: object) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("contract path must be a non-empty POSIX path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise ValueError(f"contract path escapes the snapshot: {value}")
    return path
