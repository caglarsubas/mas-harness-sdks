"""Deprecated aliases for :mod:`planeon_harness.protocols`."""

from planeon_harness.protocols import (
    MCP_COMPATIBILITY,
    MCP_CURRENT,
    MCP_SUPPORTED_VERSIONS,
    ProtocolHelperError,
    build_mcp_request,
    build_sse_resume_headers,
    classify_a2a_task_state,
    classify_mcp_task_state,
    negotiate_mcp_version,
    serialize_harness_cloud_event,
    validate_harness_cloud_event,
)

__all__ = [
    "MCP_COMPATIBILITY",
    "MCP_CURRENT",
    "MCP_SUPPORTED_VERSIONS",
    "ProtocolHelperError",
    "build_mcp_request",
    "build_sse_resume_headers",
    "classify_a2a_task_state",
    "classify_mcp_task_state",
    "negotiate_mcp_version",
    "serialize_harness_cloud_event",
    "validate_harness_cloud_event",
]
