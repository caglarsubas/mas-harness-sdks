"""Exact MCP Tasks and A2A v1 task-state classification."""

from __future__ import annotations

from typing import Any

from .errors import ProtocolHelperError


_MCP_TASK_STATES = {
    "working": ("ACTIVE", False, False, None),
    "input_required": ("INTERRUPTED", False, True, None),
    "completed": ("TERMINAL", True, False, True),
    "failed": ("TERMINAL", True, False, False),
    "cancelled": ("TERMINAL", True, False, False),
}

_A2A_TASK_STATES = {
    "TASK_STATE_SUBMITTED": ("ACTIVE", False, False, None),
    "TASK_STATE_WORKING": ("ACTIVE", False, False, None),
    "TASK_STATE_COMPLETED": ("TERMINAL", True, False, True),
    "TASK_STATE_FAILED": ("TERMINAL", True, False, False),
    "TASK_STATE_CANCELED": ("TERMINAL", True, False, False),
    "TASK_STATE_INPUT_REQUIRED": ("INTERRUPTED", False, True, None),
    "TASK_STATE_REJECTED": ("TERMINAL", True, False, False),
    "TASK_STATE_AUTH_REQUIRED": ("INTERRUPTED", False, True, None),
}


def _classification(state: object, admitted: dict[str, tuple[str, bool, bool, bool | None]], code: str) -> dict[str, Any]:
    if not isinstance(state, str) or state not in admitted:
        raise ProtocolHelperError(code, f"unsupported task state: {state!r}")
    phase, terminal, interrupted, successful = admitted[state]
    return {
        "interrupted": interrupted,
        "phase": phase,
        "state": state,
        "successful": successful,
        "terminal": terminal,
    }


def classify_mcp_task_state(state: object) -> dict[str, Any]:
    """Classify only the 2026-07-28 io.modelcontextprotocol/tasks states."""

    return _classification(state, _MCP_TASK_STATES, "INVALID_MCP_TASK_STATE")


def classify_a2a_task_state(state: object) -> dict[str, Any]:
    """Classify exact A2A v1 ProtoJSON states; unspecified fails closed."""

    return _classification(state, _A2A_TASK_STATES, "INVALID_A2A_TASK_STATE")

