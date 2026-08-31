import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import {
  buildMcpRequest,
  serializeHarnessCloudEvent,
} from "../../dist/protocols/index.js";

const vectors = JSON.parse(readFileSync("fixtures/protocols/golden-vectors.json", "utf8"));

test("committed ESM protocol surface matches golden MCP and CloudEvent bytes", () => {
  assert.deepEqual(buildMcpRequest(vectors.mcp.current.input), vectors.mcp.current.expected);
  assert.equal(serializeHarnessCloudEvent(vectors.cloudEvent.input), vectors.cloudEvent.canonicalJson);
});
