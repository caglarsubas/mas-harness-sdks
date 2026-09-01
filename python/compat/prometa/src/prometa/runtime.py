"""Deprecated aliases for :mod:`planeon_harness.runtime`."""

from planeon_harness.runtime import (
    AdmissionDecision,
    AtomicReplayStore,
    CanonicalizationError,
    ReplayReservation,
    TrustResult,
    canonical_json,
    document_digest,
    parse_json_strict,
    replay_digests,
    select_key,
    sha256_digest,
    signed_message,
    verify_admission,
    verify_bootstrap_bundle,
    verify_receipt,
    verify_rotated_bundle,
)

__all__ = [
    "AdmissionDecision",
    "AtomicReplayStore",
    "CanonicalizationError",
    "ReplayReservation",
    "TrustResult",
    "canonical_json",
    "document_digest",
    "parse_json_strict",
    "replay_digests",
    "select_key",
    "sha256_digest",
    "signed_message",
    "verify_admission",
    "verify_bootstrap_bundle",
    "verify_receipt",
    "verify_rotated_bundle",
]
