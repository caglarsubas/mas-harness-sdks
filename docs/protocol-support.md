# Protocol helper support

SDK-004 provides pure, dependency-free protocol construction and validation. It
does not open sockets, discover endpoints, persist sessions/tasks/cursors, or
make authentication and authorization decisions.

## Support matrix

| Surface | Admitted profile | SDK behavior | Fail-closed boundary |
|---|---|---|---|
| MCP | `2026-07-28` | Builds self-describing JSON-RPC requests with protocol/client metadata and matching `MCP-Protocol-Version`, `Mcp-Method`, and conditional `Mcp-Name` headers. | Rejects initialization, session headers, deprecated Roots/Sampling/Logging methods, caller-owned `_meta`, unsafe headers, and unknown versions. |
| MCP compatibility | `2025-11-25` | Builds post-initialization Streamable HTTP requests only when the caller supplies a safe session identifier. | Does not own the legacy handshake/session, inject current metadata, or silently upgrade. |
| MCP Tasks | `io.modelcontextprotocol/tasks` for `2026-07-28` | Classifies `working`, `input_required`, `completed`, `failed`, and `cancelled`. | Rejects every other value and does not bridge the incompatible 2025 experimental Tasks API. |
| A2A | v1.0 ProtoJSON task states | Classifies all eight specified non-unspecified states as active, interrupted, or terminal while preserving the exact enum. | Rejects `TASK_STATE_UNSPECIFIED`, legacy lexical aliases, and unknown states. |
| SSE resume | WHATWG `Last-Event-ID` transport field | Passes through an opaque caller-owned printable-ASCII cursor of 1-256 characters. | Does not mint, decode, sign, persist, authorize from, or normalize cursors. |
| Events | CloudEvents 1.0 structured JSON plus pinned `HarnessCloudEvent` v1alpha1 | Validates the closed event/data envelope and emits deterministic UTF-8 JSON. | Rejects extensions, unsafe numbers, invalid conditional aggregate/transition combinations, duplicate references, and malformed identifiers/timestamps. |

## Upstream specification authority

- MCP `2026-07-28`: <https://modelcontextprotocol.io/specification/2026-07-28>
- MCP `2025-11-25`: <https://modelcontextprotocol.io/specification/2025-11-25>
- MCP Tasks extension: <https://tasks.extensions.modelcontextprotocol.io/specification/draft/tasks>
- A2A v1 specification: <https://a2a-protocol.org/latest/specification/>
- CloudEvents v1.0.2: <https://github.com/cloudevents/spec/tree/ce@v1.0.2>
- WHATWG server-sent events: <https://html.spec.whatwg.org/multipage/server-sent-events.html>

The executable compatibility authority is the packet-pinned version vocabulary,
the repository contract lock for `HarnessCloudEvent`, and
`fixtures/protocols/golden-vectors.json`. Upstream pages are documentation and
do not create runtime network, dependency, or mutable-download behavior.

## Package entry points

- Python: `planeon_harness.protocols`
- TypeScript: `@planeon/harness-sdk/protocols`

Both surfaces expose the same stable denial codes through `ProtocolHelperError`.
They return data for a caller-supplied transport; neither surface sends data.
