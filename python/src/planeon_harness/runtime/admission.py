"""Fail-closed signed admission orchestration with storage-neutral replay."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any

from planeon_harness.budget import BudgetEvaluation, BudgetValidationError, evaluate_budget

from .canonical import (
    CanonicalizationError,
    base64url_decode,
    canonical_json,
    document_digest,
    require_sha256,
    sha256_digest,
    signed_message,
)
from .crypto import verify_document_signature
from .replay import AtomicReplayStore
from .trust import select_key
from .validation import DocumentValidationError, timestamp, validate_admission_envelope, validate_trust_bundle


@dataclass(frozen=True, slots=True)
class AdmissionDecision:
    admitted: bool
    reason_code: str | None
    admission_digest: str | None = None
    replay_record: Mapping[str, object] | None = None
    budget_evaluation: BudgetEvaluation | None = None
    cached_receipt: Mapping[str, object] | None = None


def _whole_second(value: datetime) -> str:
    if value.tzinfo is None or value.microsecond:
        raise ValueError("now must be timezone-aware with whole-second precision")
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _deny(reason: str, admission_digest: str | None = None) -> AdmissionDecision:
    return AdmissionDecision(False, reason, admission_digest=admission_digest)


def verify_admission(
    raw_envelope: object,
    trusted_bundle: Mapping[str, Any],
    *,
    expected_organization_id: str,
    idempotency_key_digest: str,
    limits: Mapping[str, object],
    observed: Mapping[str, object],
    replay_store: AtomicReplayStore,
    now: datetime,
) -> AdmissionDecision:
    """Apply CON-007 denial precedence and return an evidence-only decision."""

    try:
        envelope = validate_admission_envelope(raw_envelope)
        bundle = validate_trust_bundle(trusted_bundle)
        current = _whole_second(now)
    except (CanonicalizationError, DocumentValidationError, KeyError, TypeError, ValueError):
        return _deny("MALFORMED")

    admission_digest = document_digest(envelope)
    signature = envelope["signature"]
    payload = envelope["payload"]
    if sha256_digest(signed_message("SignedAdmissionEnvelope", payload)) != signature["signedMessageDigest"]:
        return _deny("DIGEST_MISMATCH", admission_digest)

    if payload["organizationId"] != expected_organization_id or bundle["payload"]["organizationId"] != expected_organization_id:
        return _deny("TENANT_MISMATCH", admission_digest)
    try:
        key, reason = select_key(
            bundle,
            key_id=signature["keyId"],
            purpose="RUNTIME_ADMISSION",
            now=now,
        )
    except (DocumentValidationError, TypeError, ValueError):
        return _deny("MALFORMED", admission_digest)
    if reason is not None or key is None:
        return _deny(reason or "SIGNER_UNKNOWN", admission_digest)
    digest_matches, signature_valid = verify_document_signature(envelope, key["publicKey"])
    if not digest_matches:
        return _deny("DIGEST_MISMATCH", admission_digest)
    if not signature_valid:
        return _deny("SIGNATURE_INVALID", admission_digest)
    if now < timestamp(payload["notBefore"], "payload.notBefore"):
        return _deny("ENVELOPE_NOT_YET_VALID", admission_digest)
    if now >= timestamp(payload["expiresAt"], "payload.expiresAt"):
        return _deny("ENVELOPE_EXPIRED", admission_digest)

    try:
        idempotency_digest = require_sha256(idempotency_key_digest, "idempotency_key_digest")
        nonce_digest = sha256_digest(
            base64url_decode(payload["nonce"], size=16, field="payload.nonce")
        )
        replay_key_digest = sha256_digest(
            canonical_json(
                {
                    "nonceDigest": nonce_digest,
                    "organizationId": payload["organizationId"],
                }
            )
        )
    except CanonicalizationError:
        return _deny("MALFORMED", admission_digest)
    if idempotency_digest != payload["idempotencyKeyDigest"]:
        return _deny("IDEMPOTENCY_CONFLICT", admission_digest)
    replay_record: dict[str, object] = {
        "apiVersion": "harness.planeon.ai/v1alpha1",
        "kind": "ReplayRecord",
        "metadata": {"id": f"{payload['admissionId']}.replay", "version": "1.0.0"},
        "spec": {
            "organizationId": payload["organizationId"],
            "replayKeyDigest": replay_key_digest,
            "idempotencyKeyDigest": idempotency_digest,
            "nonceDigest": nonce_digest,
            "admissionDigest": admission_digest,
            "requestDigest": payload["requestDigest"],
            "state": "RESERVED",
            "firstSeenAt": current,
            "updatedAt": current,
            "expiresAt": payload["expiresAt"],
            "receiptDigest": None,
        },
    }
    try:
        reservation = replay_store.reserve(MappingProxyType(replay_record))
    except Exception:
        return _deny("REPLAY_DETECTED", admission_digest)
    if reservation.status == "IDEMPOTENT":
        return AdmissionDecision(
            True,
            None,
            admission_digest=admission_digest,
            replay_record=MappingProxyType(replay_record),
            cached_receipt=reservation.cached_receipt,
        )
    if reservation.status == "IDEMPOTENCY_CONFLICT":
        return _deny("IDEMPOTENCY_CONFLICT", admission_digest)
    if reservation.status != "RESERVED":
        return _deny("REPLAY_DETECTED", admission_digest)
    try:
        budget = evaluate_budget(
            organization_id=payload["organizationId"],
            budget_digest=payload["budgetDigest"],
            admission_digest=admission_digest,
            limits=limits,
            observed=observed,
            recorded_at=now,
            record_id=f"{payload['admissionId']}.budget",
        )
    except (BudgetValidationError, CanonicalizationError, ValueError):
        return _deny("MALFORMED", admission_digest)
    if not budget.within_budget:
        return AdmissionDecision(
            False,
            "BUDGET_EXCEEDED",
            admission_digest=admission_digest,
            replay_record=MappingProxyType(replay_record),
            budget_evaluation=budget,
        )
    return AdmissionDecision(
        True,
        None,
        admission_digest=admission_digest,
        replay_record=MappingProxyType(replay_record),
        budget_evaluation=budget,
    )
