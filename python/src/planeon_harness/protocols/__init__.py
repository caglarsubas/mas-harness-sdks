"""Dependency-free protocol interoperability helpers."""

from .cloudevents import serialize_harness_cloud_event, validate_harness_cloud_event
from .errors import ProtocolHelperError
from .mcp import (
    MCP_COMPATIBILITY,
    MCP_CURRENT,
    MCP_SUPPORTED_VERSIONS,
    build_mcp_request,
    negotiate_mcp_version,
)
from .sse import build_sse_resume_headers
from .tasks import classify_a2a_task_state, classify_mcp_task_state

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
