"""Opaque Last-Event-ID handling without token interpretation."""

from __future__ import annotations

from .errors import ProtocolHelperError


def build_sse_resume_headers(last_event_id: object) -> dict[str, str]:
    """Return resumable SSE headers while preserving the caller-owned cursor exactly."""

    if (
        not isinstance(last_event_id, str)
        or not 1 <= len(last_event_id) <= 256
        or any(ord(character) < 0x20 or ord(character) > 0x7E for character in last_event_id)
    ):
        raise ProtocolHelperError(
            "UNSAFE_RESUME_CURSOR",
            "Last-Event-ID must contain 1-256 printable ASCII characters",
        )
    return {"Accept": "text/event-stream", "Last-Event-ID": last_event_id}

