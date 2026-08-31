"""Public runtime admission and trust API."""

from .admission import AdmissionDecision, verify_admission
from .canonical import (
    CanonicalizationError,
    canonical_json,
    document_digest,
    parse_json_strict,
    replay_digests,
    sha256_digest,
    signed_message,
)
from .replay import AtomicReplayStore, ReplayReservation
from .trust import (
    TrustResult,
    select_key,
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
