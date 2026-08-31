"""Storage-neutral atomic replay/idempotency contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class ReplayReservation:
    """Atomic adapter outcome; a cached receipt is permitted only for IDEMPOTENT."""

    status: str
    existing_request_digest: str | None = None
    cached_receipt: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        if self.status not in {"RESERVED", "IDEMPOTENT", "IDEMPOTENCY_CONFLICT", "REPLAY_DETECTED"}:
            raise ValueError(f"unknown replay reservation status: {self.status}")
        if self.status == "IDEMPOTENT" and self.cached_receipt is None:
            raise ValueError("idempotent reservation must return its committed signed receipt")
        if self.status != "IDEMPOTENT" and self.cached_receipt is not None:
            raise ValueError("only an idempotent reservation may return a cached receipt")


@runtime_checkable
class AtomicReplayStore(Protocol):
    """Caller-owned persistence must reserve both keys in one transaction."""

    def reserve(self, record: Mapping[str, object]) -> ReplayReservation:
        """Atomically reserve idempotency and replay digests, or fail closed."""

    def commit(
        self,
        record: Mapping[str, object],
        *,
        receipt_digest: str,
        accepted: bool,
    ) -> Mapping[str, object]:
        """Atomically bind the reserved record to its immutable receipt."""
