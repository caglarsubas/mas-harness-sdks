"""Bootstrap, rotation, exact-key selection, and receipt trust."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any

from .canonical import CanonicalizationError, document_digest
from .crypto import verify_document_signature
from .validation import DocumentValidationError, timestamp, validate_receipt, validate_trust_bundle


@dataclass(frozen=True, slots=True)
class TrustResult:
    accepted: bool
    reason_code: str | None
    document_digest: str | None = None


def select_key(
    trust_bundle: Mapping[str, Any],
    *,
    key_id: str,
    purpose: str,
    now: datetime,
) -> tuple[Mapping[str, Any] | None, str | None]:
    """Select one exact key and return the closed first failure reason."""

    keys = trust_bundle["payload"]["keys"]
    selected = next((key for key in keys if key["keyId"] == key_id), None)
    if selected is None:
        return None, "SIGNER_UNKNOWN"
    if selected["state"] == "REVOKED":
        return None, "SIGNER_REVOKED"
    if selected["state"] != "ACTIVE":
        return None, "SIGNER_NOT_ACTIVE"
    if purpose not in selected["purposes"]:
        return None, "KEY_PURPOSE_MISMATCH"
    if not timestamp(selected["notBefore"], "key.notBefore") <= now < timestamp(selected["notAfter"], "key.notAfter"):
        return None, "SIGNER_NOT_ACTIVE"
    return MappingProxyType(dict(selected)), None


def verify_bootstrap_bundle(
    raw_bundle: object,
    *,
    pinned_digest: str,
    expected_organization_id: str,
    now: datetime,
) -> TrustResult:
    """Adopt only a digest-pinned, self-consistent bootstrap trust root."""

    try:
        bundle = validate_trust_bundle(raw_bundle)
        digest = document_digest(bundle)
        if digest != pinned_digest:
            return TrustResult(False, "DIGEST_MISMATCH")
        if bundle["payload"]["organizationId"] != expected_organization_id:
            return TrustResult(False, "TENANT_MISMATCH")
        if not timestamp(bundle["payload"]["validFrom"], "payload.validFrom") <= now < timestamp(bundle["payload"]["validUntil"], "payload.validUntil"):
            return TrustResult(False, "SIGNER_NOT_ACTIVE")
        signature = bundle["signature"]
        key, reason = select_key(
            bundle,
            key_id=signature["keyId"],
            purpose="TRUST_BUNDLE",
            now=now,
        )
        if reason is not None or key is None:
            return TrustResult(False, reason)
        digest_matches, signature_valid = verify_document_signature(bundle, key["publicKey"])
        if not digest_matches:
            return TrustResult(False, "DIGEST_MISMATCH")
        if not signature_valid:
            return TrustResult(False, "SIGNATURE_INVALID")
        if bundle["payload"]["bundleVersion"] != 1 or bundle["payload"]["previousBundleDigest"] is not None:
            return TrustResult(False, "MALFORMED")
        return TrustResult(True, None, digest)
    except (CanonicalizationError, DocumentValidationError, KeyError, TypeError, ValueError):
        return TrustResult(False, "MALFORMED")


def verify_rotated_bundle(
    raw_candidate: object,
    trusted_predecessor: Mapping[str, Any],
    *,
    expected_organization_id: str,
    now: datetime,
) -> TrustResult:
    """Verify a strict +1 rotation signed by one predecessor trust key."""

    try:
        predecessor = validate_trust_bundle(trusted_predecessor)
        candidate = validate_trust_bundle(raw_candidate)
        if candidate["payload"]["organizationId"] != expected_organization_id or predecessor["payload"]["organizationId"] != expected_organization_id:
            return TrustResult(False, "TENANT_MISMATCH")
        if candidate["payload"]["bundleVersion"] != predecessor["payload"]["bundleVersion"] + 1:
            return TrustResult(False, "MALFORMED")
        if candidate["payload"]["previousBundleDigest"] != document_digest(predecessor):
            return TrustResult(False, "DIGEST_MISMATCH")
        signature = candidate["signature"]
        key, reason = select_key(predecessor, key_id=signature["keyId"], purpose="TRUST_BUNDLE", now=now)
        if reason is not None or key is None:
            return TrustResult(False, reason)
        digest_matches, signature_valid = verify_document_signature(candidate, key["publicKey"])
        if not digest_matches:
            return TrustResult(False, "DIGEST_MISMATCH")
        if not signature_valid:
            return TrustResult(False, "SIGNATURE_INVALID")
        return TrustResult(True, None, document_digest(candidate))
    except (CanonicalizationError, DocumentValidationError, KeyError, TypeError, ValueError):
        return TrustResult(False, "MALFORMED")


def verify_receipt(
    raw_receipt: object,
    trusted_bundle: Mapping[str, Any],
    *,
    expected_organization_id: str,
    now: datetime,
) -> TrustResult:
    """Verify receipt identity, exact key, signature, and validity window."""

    try:
        bundle = validate_trust_bundle(trusted_bundle)
        receipt = validate_receipt(raw_receipt)
        signature = receipt["signature"]
        message_digest = document_digest(receipt)
        if receipt["payload"]["organizationId"] != expected_organization_id or bundle["payload"]["organizationId"] != expected_organization_id:
            return TrustResult(False, "TENANT_MISMATCH")
        key, reason = select_key(bundle, key_id=signature["keyId"], purpose="RUNTIME_RECEIPT", now=now)
        if reason is not None or key is None:
            return TrustResult(False, reason)
        digest_matches, signature_valid = verify_document_signature(receipt, key["publicKey"])
        if not digest_matches:
            return TrustResult(False, "DIGEST_MISMATCH")
        if not signature_valid:
            return TrustResult(False, "SIGNATURE_INVALID")
        if now >= timestamp(receipt["payload"]["expiresAt"], "payload.expiresAt"):
            return TrustResult(False, "ENVELOPE_EXPIRED")
        return TrustResult(True, None, message_digest)
    except (CanonicalizationError, DocumentValidationError, KeyError, TypeError, ValueError):
        return TrustResult(False, "MALFORMED")
