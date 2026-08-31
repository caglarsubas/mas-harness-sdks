"""Closed semantic validation for CON-007 runtime documents."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from .canonical import CanonicalizationError, base64url_decode, require_sha256


API_VERSION = "harness.planeon.ai/v1alpha1"
PROFILE = "RFC8785_JCS_ED25519_V1"
ALGORITHM = "ED25519"
PURPOSES = frozenset({"RUNTIME_ADMISSION", "RUNTIME_RECEIPT", "TRUST_BUNDLE"})
DENIAL_REASONS = frozenset(
    {
        "MALFORMED",
        "SIGNATURE_INVALID",
        "SIGNER_UNKNOWN",
        "SIGNER_NOT_ACTIVE",
        "SIGNER_REVOKED",
        "KEY_PURPOSE_MISMATCH",
        "ENVELOPE_NOT_YET_VALID",
        "ENVELOPE_EXPIRED",
        "TENANT_MISMATCH",
        "REPLAY_DETECTED",
        "IDEMPOTENCY_CONFLICT",
        "BUDGET_EXCEEDED",
        "DIGEST_MISMATCH",
    }
)
_STABLE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)+$")
_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_TIMESTAMP = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")


class DocumentValidationError(CanonicalizationError):
    """Raised when a signed document is outside its closed schema."""


def _object(value: object, fields: set[str], context: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise DocumentValidationError(f"{context} must be an object")
    result = dict(value)
    if set(result) != fields:
        raise DocumentValidationError(f"{context} fields are closed")
    return result


def _string(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.isascii():
        raise DocumentValidationError(f"{context} must be an ASCII string")
    return value


def _stable_id(value: object, context: str) -> str:
    result = _string(value, context)
    if _STABLE_ID.fullmatch(result) is None or len(result) > 128:
        raise DocumentValidationError(f"{context} is not a stable identifier")
    return result


def timestamp(value: object, context: str) -> datetime:
    result = _string(value, context)
    if _TIMESTAMP.fullmatch(result) is None:
        raise DocumentValidationError(f"{context} must be a whole-second UTC timestamp")
    try:
        return datetime.strptime(result, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise DocumentValidationError(f"{context} is not a calendar timestamp") from exc


def _metadata(value: object) -> dict[str, Any]:
    metadata = _object(value, {"id", "version"}, "metadata")
    _stable_id(metadata["id"], "metadata.id")
    version = _string(metadata["version"], "metadata.version")
    if _SEMVER.fullmatch(version) is None:
        raise DocumentValidationError("metadata.version must be semantic version core")
    return metadata


def _signature(value: object, purpose: str) -> dict[str, Any]:
    signature = _object(
        value,
        {"profile", "algorithm", "purpose", "keyId", "signedMessageDigest", "value"},
        "signature",
    )
    if signature["profile"] != PROFILE or signature["algorithm"] != ALGORITHM:
        raise DocumentValidationError("signature profile or algorithm is unsupported")
    if signature["purpose"] != purpose:
        raise DocumentValidationError("signature purpose differs from document kind")
    _stable_id(signature["keyId"], "signature.keyId")
    require_sha256(signature["signedMessageDigest"], "signature.signedMessageDigest")
    base64url_decode(signature["value"], size=64, field="signature.value")
    return signature


def _signed_document(value: object, kind: str, purpose: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    document = _object(value, {"apiVersion", "kind", "metadata", "payload", "signature"}, kind)
    if document["apiVersion"] != API_VERSION or document["kind"] != kind:
        raise DocumentValidationError(f"{kind} identity is invalid")
    _metadata(document["metadata"])
    signature = _signature(document["signature"], purpose)
    if not isinstance(document["payload"], Mapping):
        raise DocumentValidationError(f"{kind}.payload must be an object")
    return document, dict(document["payload"]), signature


def validate_trust_bundle(value: object) -> dict[str, Any]:
    document, payload_value, _signature_value = _signed_document(value, "RuntimeTrustBundle", "TRUST_BUNDLE")
    payload = _object(
        payload_value,
        {"organizationId", "bundleVersion", "issuedAt", "validFrom", "validUntil", "previousBundleDigest", "keys"},
        "RuntimeTrustBundle.payload",
    )
    _stable_id(payload["organizationId"], "payload.organizationId")
    if not isinstance(payload["bundleVersion"], int) or isinstance(payload["bundleVersion"], bool) or not 1 <= payload["bundleVersion"] <= 2_147_483_647:
        raise DocumentValidationError("payload.bundleVersion is out of range")
    issued = timestamp(payload["issuedAt"], "payload.issuedAt")
    valid_from = timestamp(payload["validFrom"], "payload.validFrom")
    valid_until = timestamp(payload["validUntil"], "payload.validUntil")
    if not issued <= valid_from < valid_until:
        raise DocumentValidationError("trust bundle timestamps are not ordered")
    if payload["previousBundleDigest"] is not None:
        require_sha256(payload["previousBundleDigest"], "payload.previousBundleDigest")
    keys = payload["keys"]
    if not isinstance(keys, list) or not 1 <= len(keys) <= 128:
        raise DocumentValidationError("payload.keys must contain 1-128 keys")
    seen: set[str] = set()
    for index, raw_key in enumerate(keys):
        key = _object(
            raw_key,
            {"keyId", "algorithm", "publicKey", "purposes", "state", "notBefore", "notAfter", "revokedAt", "revocationReason"},
            f"payload.keys[{index}]",
        )
        key_id = _stable_id(key["keyId"], f"payload.keys[{index}].keyId")
        if key_id in seen:
            raise DocumentValidationError("payload.keys contains duplicate keyId")
        seen.add(key_id)
        if key["algorithm"] != ALGORITHM:
            raise DocumentValidationError("trust key algorithm is unsupported")
        base64url_decode(key["publicKey"], size=32, field=f"payload.keys[{index}].publicKey")
        purposes = key["purposes"]
        if not isinstance(purposes, list) or not purposes or len(purposes) != len(set(purposes)) or not set(purposes) <= PURPOSES:
            raise DocumentValidationError("trust key purposes are invalid")
        if key["state"] not in {"PENDING", "ACTIVE", "RETIRED", "REVOKED"}:
            raise DocumentValidationError("trust key state is invalid")
        not_before = timestamp(key["notBefore"], f"payload.keys[{index}].notBefore")
        not_after = timestamp(key["notAfter"], f"payload.keys[{index}].notAfter")
        if not_before >= not_after:
            raise DocumentValidationError("trust key timestamps are not ordered")
        if key["state"] == "REVOKED":
            revoked = timestamp(key["revokedAt"], f"payload.keys[{index}].revokedAt")
            if revoked < not_before or key["revocationReason"] not in {"KEY_COMPROMISE", "AUTHORITY_WITHDRAWN", "SUPERSEDED", "POLICY_VIOLATION"}:
                raise DocumentValidationError("revoked trust key metadata is invalid")
        elif key["revokedAt"] is not None or key["revocationReason"] is not None:
            raise DocumentValidationError("non-revoked trust key carries revocation metadata")
    return document


def validate_admission_envelope(value: object) -> dict[str, Any]:
    document, payload_value, _signature_value = _signed_document(value, "SignedAdmissionEnvelope", "RUNTIME_ADMISSION")
    payload = _object(
        payload_value,
        {"organizationId", "admissionId", "subjectDigest", "releaseDigest", "policyDigest", "budgetDigest", "requestDigest", "operation", "issuedAt", "notBefore", "expiresAt", "nonce", "idempotencyKeyDigest"},
        "SignedAdmissionEnvelope.payload",
    )
    _stable_id(payload["organizationId"], "payload.organizationId")
    _stable_id(payload["admissionId"], "payload.admissionId")
    for field in ("subjectDigest", "releaseDigest", "policyDigest", "budgetDigest", "requestDigest", "idempotencyKeyDigest"):
        require_sha256(payload[field], f"payload.{field}")
    if payload["operation"] not in {"MODEL_INFERENCE", "AGENT_RUN", "TOOL_EXECUTION", "WORKFLOW_RESUME"}:
        raise DocumentValidationError("payload.operation is invalid")
    issued = timestamp(payload["issuedAt"], "payload.issuedAt")
    not_before = timestamp(payload["notBefore"], "payload.notBefore")
    expires = timestamp(payload["expiresAt"], "payload.expiresAt")
    if not issued <= not_before < expires:
        raise DocumentValidationError("admission envelope timestamps are not ordered")
    base64url_decode(payload["nonce"], size=16, field="payload.nonce")
    return document


def validate_receipt(value: object) -> dict[str, Any]:
    document, payload_value, _signature_value = _signed_document(value, "RuntimeAdmissionReceipt", "RUNTIME_RECEIPT")
    payload = _object(
        payload_value,
        {"organizationId", "receiptId", "admissionDigest", "requestDigest", "trustBundleDigest", "decision", "reasonCode", "budgetConsumptionDigest", "replayRecordDigest", "decidedAt", "expiresAt"},
        "RuntimeAdmissionReceipt.payload",
    )
    _stable_id(payload["organizationId"], "payload.organizationId")
    _stable_id(payload["receiptId"], "payload.receiptId")
    for field in ("admissionDigest", "requestDigest", "trustBundleDigest"):
        require_sha256(payload[field], f"payload.{field}")
    if payload["decision"] not in {"ADMIT", "DENY"}:
        raise DocumentValidationError("payload.decision is invalid")
    if payload["decision"] == "ADMIT":
        if payload["reasonCode"] is not None:
            raise DocumentValidationError("admitted receipt cannot have a reason")
        require_sha256(payload["budgetConsumptionDigest"], "payload.budgetConsumptionDigest")
        require_sha256(payload["replayRecordDigest"], "payload.replayRecordDigest")
    else:
        if payload["reasonCode"] not in DENIAL_REASONS:
            raise DocumentValidationError("denied receipt reason is invalid")
        for field in ("budgetConsumptionDigest", "replayRecordDigest"):
            if payload[field] is not None:
                require_sha256(payload[field], f"payload.{field}")
    decided = timestamp(payload["decidedAt"], "payload.decidedAt")
    expires = timestamp(payload["expiresAt"], "payload.expiresAt")
    if decided >= expires:
        raise DocumentValidationError("receipt timestamps are not ordered")
    return document
