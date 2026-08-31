"""Pure request construction for the two admitted MCP revisions."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from ._json import MAX_SAFE_INTEGER, detached_json
from .errors import ProtocolHelperError


MCP_CURRENT = "2026-07-28"
MCP_COMPATIBILITY = "2025-11-25"
MCP_SUPPORTED_VERSIONS = (MCP_CURRENT, MCP_COMPATIBILITY)

_METHOD = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*(?:/[A-Za-z][A-Za-z0-9._-]*)*$")
_DEPRECATED_PREFIXES = ("roots/", "sampling/", "logging/")
_NAMED_METHOD_FIELDS = {
    "tools/call": "name",
    "resources/read": "uri",
    "prompts/get": "name",
}
_SESSION_ID = re.compile(r"^[A-Za-z0-9._~-]{1,128}$")


def _visible_ascii(value: object, field: str, maximum: int = 128) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= maximum
        or any(ord(character) < 0x20 or ord(character) > 0x7E for character in value)
    ):
        raise ProtocolHelperError("INVALID_MCP_REQUEST", f"{field} must be bounded printable ASCII")
    return value


def negotiate_mcp_version(offered: Sequence[str]) -> str:
    """Select the newest exact supported revision without an implicit fallback."""

    if (
        isinstance(offered, (str, bytes, bytearray))
        or not isinstance(offered, Sequence)
        or not offered
        or not all(isinstance(version, str) for version in offered)
    ):
        raise ProtocolHelperError("UNSUPPORTED_PROTOCOL_VERSION", "MCP versions must be an ordered sequence")
    if MCP_CURRENT in offered:
        return MCP_CURRENT
    if MCP_COMPATIBILITY in offered:
        return MCP_COMPATIBILITY
    raise ProtocolHelperError("UNSUPPORTED_PROTOCOL_VERSION", "no admitted MCP revision was offered")


def build_mcp_request(
    *,
    version: str,
    request_id: str | int,
    method: str,
    params: Mapping[str, Any],
    client_name: str | None = None,
    client_version: str | None = None,
    client_capabilities: Mapping[str, Any] | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Build one transport-neutral JSON-RPC request plus Streamable HTTP headers."""

    if version not in MCP_SUPPORTED_VERSIONS:
        raise ProtocolHelperError("UNSUPPORTED_PROTOCOL_VERSION", f"unsupported MCP revision: {version}")
    if isinstance(request_id, bool) or not isinstance(request_id, (str, int)):
        raise ProtocolHelperError("INVALID_MCP_REQUEST", "request_id must be a string or integer")
    if isinstance(request_id, int) and not -MAX_SAFE_INTEGER <= request_id <= MAX_SAFE_INTEGER:
        raise ProtocolHelperError("INVALID_MCP_REQUEST", "request_id integer is outside the safe JSON range")
    if isinstance(request_id, str):
        _visible_ascii(request_id, "request_id")
    if not isinstance(method, str) or _METHOD.fullmatch(method) is None:
        raise ProtocolHelperError("INVALID_MCP_REQUEST", "method is not a valid MCP method name")
    if method.startswith(_DEPRECATED_PREFIXES):
        raise ProtocolHelperError("DEPRECATED_MCP_METHOD", f"deprecated MCP method is not admitted: {method}")
    if not isinstance(params, Mapping) or not all(isinstance(key, str) for key in params):
        raise ProtocolHelperError("INVALID_MCP_REQUEST", "params must be a JSON object")
    body_params = detached_json(params)
    if not isinstance(body_params, dict):
        raise ProtocolHelperError("INVALID_MCP_REQUEST", "params must be a JSON object")

    headers: dict[str, str] = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "MCP-Protocol-Version": version,
    }
    if version == MCP_CURRENT:
        if method in {"initialize", "notifications/initialized"}:
            raise ProtocolHelperError("LEGACY_HANDSHAKE_FORBIDDEN", "2026-07-28 has no initialize handshake")
        if session_id is not None:
            raise ProtocolHelperError("MCP_SESSION_FORBIDDEN", "2026-07-28 requests are session-free")
        if "_meta" in body_params:
            raise ProtocolHelperError("INVALID_MCP_REQUEST", "caller-supplied _meta would shadow protocol identity")
        capabilities = detached_json(client_capabilities or {})
        if not isinstance(capabilities, dict):
            raise ProtocolHelperError("INVALID_MCP_REQUEST", "client_capabilities must be a JSON object")
        body_params["_meta"] = {
            "io.modelcontextprotocol/clientCapabilities": capabilities,
            "io.modelcontextprotocol/clientInfo": {
                "name": _visible_ascii(client_name, "client_name"),
                "version": _visible_ascii(client_version, "client_version"),
            },
            "io.modelcontextprotocol/protocolVersion": MCP_CURRENT,
        }
        headers["Mcp-Method"] = method
        name_field = _NAMED_METHOD_FIELDS.get(method)
        if name_field is not None:
            if name_field not in body_params:
                raise ProtocolHelperError("MCP_NAME_REQUIRED", f"{method} requires params.{name_field}")
            headers["Mcp-Name"] = _visible_ascii(body_params[name_field], f"params.{name_field}", 1024)
    else:
        if client_name is not None or client_version is not None or client_capabilities is not None:
            raise ProtocolHelperError("INVALID_MCP_REQUEST", "2025 compatibility identity is established by initialize")
        if method in {"initialize", "notifications/initialized"}:
            raise ProtocolHelperError("LEGACY_HANDSHAKE_EXTERNAL", "the compatibility helper does not own legacy initialization")
        if not isinstance(session_id, str) or _SESSION_ID.fullmatch(session_id) is None:
            raise ProtocolHelperError("LEGACY_SESSION_REQUIRED", "2025-11-25 requests require an admitted session id")
        headers["Mcp-Session-Id"] = session_id

    return {
        "body": {"id": request_id, "jsonrpc": "2.0", "method": method, "params": body_params},
        "headers": headers,
        "version": version,
    }
