"""Bounded official MCP Python client invocation adapter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from planeon_harness.decorators import SpanSink
from planeon_harness.protocols import MCP_CURRENT, negotiate_mcp_version

from ._base import invoke_async, require_integration, require_methods


class MCPClientAdapter:
    """Expose only explicit tool calls against one admitted MCP revision."""

    __slots__ = ("_client", "_sink", "protocol_version")

    def __init__(self, client: object, protocol_version: str, sink: SpanSink | None) -> None:
        self._client = client
        self._sink = sink
        self.protocol_version = protocol_version

    async def call_tool(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        return await invoke_async(
            self._client.call_tool,
            "harness.integration.mcp.call_tool",
            self._sink,
            (name, arguments),
            kwargs,
        )


def instrument_mcp_client(
    client: object,
    *,
    protocol_version: str = MCP_CURRENT,
    sink: SpanSink | None = None,
) -> MCPClientAdapter:
    """Validate the official SDK and protocol revision without opening a session."""

    require_integration("mcp")
    admitted_version = negotiate_mcp_version((protocol_version,))
    require_methods("mcp", client, ("call_tool",))
    return MCPClientAdapter(client, admitted_version, sink)
