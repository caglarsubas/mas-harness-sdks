"""Ed25519 verification through the audited ``cryptography`` package."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .canonical import base64url_decode, sha256_digest, signed_message


def verify_document_signature(
    document: Mapping[str, Any],
    public_key_base64url: str,
) -> tuple[bool, bool]:
    """Return ``(digest_matches, signature_valid)`` without key fallback."""

    kind = document["kind"]
    payload = document["payload"]
    signature = document["signature"]
    message = signed_message(kind, payload)
    if sha256_digest(message) != signature["signedMessageDigest"]:
        return False, False
    public_key = Ed25519PublicKey.from_public_bytes(
        base64url_decode(public_key_base64url, size=32, field="publicKey")
    )
    signature_bytes = base64url_decode(signature["value"], size=64, field="signature.value")
    try:
        public_key.verify(signature_bytes, message)
    except InvalidSignature:
        return True, False
    return True, True
