"""Fail-closed authorization helpers for admission decisions."""

from __future__ import annotations

from typing import Protocol


class AdmittedDecision(Protocol):
    admitted: bool
    reason_code: str | None


class AuthorizationDenied(PermissionError):
    """Raised when a mutation is attempted without an admitted decision."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(f"runtime admission denied: {reason_code}")
        self.reason_code = reason_code


def require_admitted(decision: AdmittedDecision) -> None:
    """Refuse execution unless admission is explicit and reason-free."""

    if decision.admitted is not True or decision.reason_code is not None:
        raise AuthorizationDenied(decision.reason_code or "MALFORMED")
