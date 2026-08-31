"""Closed RFC 8785 profile used by the runtime-admission contracts."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


DOMAINS = {
    "RuntimeTrustBundle": "harness.planeon.ai/runtime-trust-bundle/v1alpha1",
    "SignedAdmissionEnvelope": "harness.planeon.ai/runtime-admission/v1alpha1",
    "RuntimeAdmissionReceipt": "harness.planeon.ai/runtime-admission-receipt/v1alpha1",
}
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


class CanonicalizationError(ValueError):
    """Raised when input falls outside the signed I-JSON profile."""


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CanonicalizationError(f"duplicate JSON property: {key}")
        result[key] = value
    return result


def parse_json_strict(raw: str | bytes | bytearray) -> Any:
    """Parse JSON while rejecting duplicate properties and non-I-JSON numbers."""

    if isinstance(raw, (bytes, bytearray)):
        try:
            text = bytes(raw).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CanonicalizationError("signed JSON must be UTF-8") from exc
    elif isinstance(raw, str):
        text = raw
    else:
        raise CanonicalizationError("signed JSON input must be text or bytes")
    try:
        return json.loads(
            text,
            object_pairs_hook=_no_duplicates,
            parse_float=lambda _value: (_ for _ in ()).throw(
                CanonicalizationError("signed JSON forbids floating-point numbers")
            ),
            parse_constant=lambda _value: (_ for _ in ()).throw(
                CanonicalizationError("signed JSON forbids non-finite numbers")
            ),
        )
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise CanonicalizationError("signed JSON is malformed") from exc


def _validate_profile(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if not -(2**53 - 1) <= value <= 2**53 - 1:
            raise CanonicalizationError(f"integer is outside the I-JSON safe range: {path}")
        return
    if isinstance(value, float):
        raise CanonicalizationError(f"signed JSON forbids floating-point numbers: {path}")
    if isinstance(value, str):
        if not value.isascii():
            raise CanonicalizationError(f"signed JSON strings must be ASCII in v1alpha1: {path}")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str) or not key.isascii():
                raise CanonicalizationError(f"signed JSON property names must be ASCII: {path}")
            _validate_profile(item, f"{path}.{key}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            _validate_profile(item, f"{path}[{index}]")
        return
    raise CanonicalizationError(f"unsupported signed JSON value: {path}")


def canonical_json(value: Any) -> bytes:
    """Return RFC 8785 bytes for the contracts' stricter integer/ASCII subset."""

    _validate_profile(value)
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def base64url_decode(value: str, *, size: int, field: str) -> bytes:
    if not isinstance(value, str) or "=" in value or not value.isascii():
        raise CanonicalizationError(f"{field} must be unpadded base64url")
    try:
        decoded = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    except (ValueError, binascii.Error) as exc:
        raise CanonicalizationError(f"{field} must be unpadded base64url") from exc
    if len(decoded) != size:
        raise CanonicalizationError(f"{field} must decode to {size} bytes")
    return decoded


def sha256_digest(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def require_sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        raise CanonicalizationError(f"{field} must be a lower-case SHA-256 digest")
    return value


def signed_message(kind: str, payload: Mapping[str, Any]) -> bytes:
    try:
        domain = DOMAINS[kind]
    except KeyError as exc:
        raise CanonicalizationError(f"unsupported signed document kind: {kind}") from exc
    return domain.encode("ascii") + b"\0" + canonical_json(payload)


def document_digest(document: Mapping[str, Any]) -> str:
    return sha256_digest(canonical_json(document))


def replay_digests(
    *, organization_id: str, nonce: str, raw_idempotency_key: str
) -> tuple[str, str, str]:
    if not isinstance(raw_idempotency_key, str) or not 16 <= len(raw_idempotency_key) <= 128:
        raise CanonicalizationError("raw idempotency key must contain 16-128 characters")
    try:
        encoded_key = raw_idempotency_key.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise CanonicalizationError("raw idempotency key must be UTF-8") from exc
    nonce_digest = sha256_digest(base64url_decode(nonce, size=16, field="nonce"))
    idempotency_digest = sha256_digest(encoded_key)
    replay_key = sha256_digest(
        canonical_json({"nonceDigest": nonce_digest, "organizationId": organization_id})
    )
    return idempotency_digest, nonce_digest, replay_key
