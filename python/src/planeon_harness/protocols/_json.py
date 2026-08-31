"""Deterministic JSON subset shared by protocol helpers."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from .errors import ProtocolHelperError


MAX_SAFE_INTEGER = 2**53 - 1


def validate_json(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, bool) or isinstance(value, str):
        return
    if isinstance(value, int):
        if not -MAX_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER:
            raise ProtocolHelperError("INVALID_JSON_VALUE", f"unsafe JSON integer at {path}")
        return
    if isinstance(value, float):
        raise ProtocolHelperError("INVALID_JSON_VALUE", f"floating-point JSON is not deterministic at {path}")
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ProtocolHelperError("INVALID_JSON_VALUE", f"non-string JSON key at {path}")
            validate_json(item, f"{path}.{key}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            validate_json(item, f"{path}[{index}]")
        return
    raise ProtocolHelperError("INVALID_JSON_VALUE", f"unsupported JSON value at {path}")


def deterministic_json_bytes(value: Any) -> bytes:
    validate_json(value)
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def detached_json(value: Any) -> Any:
    """Return a JSON-only detached copy after closed validation."""

    return json.loads(deterministic_json_bytes(value))

