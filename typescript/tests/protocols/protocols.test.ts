import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import {
  MCP_COMPATIBILITY,
  MCP_CURRENT,
  ProtocolHelperError,
  buildMcpRequest,
  buildSseResumeHeaders,
  classifyA2aTaskState,
  classifyMcpTaskState,
  negotiateMcpVersion,
  serializeHarnessCloudEvent,
  validateHarnessCloudEvent,
} from "../../src/protocols/index.ts";

const vectors = JSON.parse(readFileSync("fixtures/protocols/golden-vectors.json", "utf8"));

test("current and compatibility MCP vectors are byte-equivalent", () => {
  const currentInput = structuredClone(vectors.mcp.current.input);
  const compatibilityInput = structuredClone(vectors.mcp.compatibility.input);
  assert.deepEqual(buildMcpRequest(currentInput), vectors.mcp.current.expected);
  assert.deepEqual(buildMcpRequest(compatibilityInput), vectors.mcp.compatibility.expected);
  assert.deepEqual(currentInput, vectors.mcp.current.input);
  assert.equal(negotiateMcpVersion([MCP_COMPATIBILITY, MCP_CURRENT]), MCP_CURRENT);
  assert.throws(
    () => negotiateMcpVersion([MCP_CURRENT, null] as unknown as string[]),
    (error: unknown) => error instanceof ProtocolHelperError && error.code === "UNSUPPORTED_PROTOCOL_VERSION",
  );
});

test("MCP and A2A task states match every golden classification", () => {
  assert.deepEqual(
    Object.fromEntries(Object.keys(vectors.mcpTaskStates).map((state) => [state, classifyMcpTaskState(state)])),
    vectors.mcpTaskStates,
  );
  assert.deepEqual(
    Object.fromEntries(Object.keys(vectors.a2aTaskStates).map((state) => [state, classifyA2aTaskState(state)])),
    vectors.a2aTaskStates,
  );
});

test("SSE cursor remains opaque and CloudEvent bytes remain deterministic", () => {
  assert.deepEqual(buildSseResumeHeaders(vectors.sse.cursor), vectors.sse.expected);
  assert.deepEqual(validateHarnessCloudEvent(vectors.cloudEvent.input), vectors.cloudEvent.input);
  assert.equal(serializeHarnessCloudEvent(vectors.cloudEvent.input), vectors.cloudEvent.canonicalJson);
});

test("unsupported versions, deprecated methods, and legacy session gaps fail closed", () => {
  const cases = [
    [{ ...vectors.mcp.current.input, version: "2025-06-18" }, "UNSUPPORTED_PROTOCOL_VERSION"],
    [{ ...vectors.mcp.current.input, method: "sampling/createMessage" }, "DEPRECATED_MCP_METHOD"],
    [{ ...vectors.mcp.current.input, sessionId: "unexpected" }, "MCP_SESSION_FORBIDDEN"],
    [{ ...vectors.mcp.compatibility.input, sessionId: undefined }, "LEGACY_SESSION_REQUIRED"],
  ];
  for (const [input, reason] of cases) {
    assert.throws(
      () => buildMcpRequest(input),
      (error: unknown) => error instanceof ProtocolHelperError && error.code === reason,
    );
  }
});

test("invalid task states, unsafe cursors, and malformed events fail closed", () => {
  assert.throws(
    () => classifyMcpTaskState("submitted"),
    (error: unknown) => error instanceof ProtocolHelperError && error.code === "INVALID_MCP_TASK_STATE",
  );
  assert.throws(
    () => classifyA2aTaskState("TASK_STATE_UNSPECIFIED"),
    (error: unknown) => error instanceof ProtocolHelperError && error.code === "INVALID_A2A_TASK_STATE",
  );
  assert.throws(
    () => buildSseResumeHeaders("event\nnext"),
    (error: unknown) => error instanceof ProtocolHelperError && error.code === "UNSAFE_RESUME_CURSOR",
  );
  assert.throws(
    () => validateHarnessCloudEvent({ ...vectors.cloudEvent.input, extension: "forbidden" }),
    (error: unknown) => error instanceof ProtocolHelperError && error.code === "MALFORMED_CLOUD_EVENT",
  );
});
