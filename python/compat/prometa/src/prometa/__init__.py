"""Deprecated migration aliases for the canonical Planeon harness SDK."""

import warnings as _warnings

from planeon_harness import (
    CHANNELS,
    CONTRACT_RELEASE_DIGEST,
    AdmissionDecision,
    HarnessClient,
    ReplayReservation,
    Request,
    TrustResult,
    __version__,
    verify_admission,
    verify_bootstrap_bundle,
    verify_receipt,
    verify_rotated_bundle,
)

_warnings.warn(
    "The prometa import is deprecated; use planeon_harness. It is supported only through planeon-harness-sdk v1 and will be removed in v2.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "CHANNELS",
    "CONTRACT_RELEASE_DIGEST",
    "HarnessClient",
    "Request",
    "AdmissionDecision",
    "ReplayReservation",
    "TrustResult",
    "verify_admission",
    "verify_bootstrap_bundle",
    "verify_receipt",
    "verify_rotated_bundle",
    "__version__",
]

del _warnings
