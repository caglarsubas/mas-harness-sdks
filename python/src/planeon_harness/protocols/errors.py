"""Closed failure surface for dependency-free protocol helpers."""

from __future__ import annotations


class ProtocolHelperError(ValueError):
    """Fail-closed protocol error with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code

