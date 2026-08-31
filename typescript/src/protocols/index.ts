/** Dependency-free MCP, task, SSE, and HarnessCloudEvent helpers. */

export type JsonPrimitive = null | boolean | number | string;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };
export type JsonObject = { [key: string]: JsonValue };

export class ProtocolHelperError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "ProtocolHelperError";
    this.code = code;
  }
}

const MAX_SAFE_INTEGER = Number.MAX_SAFE_INTEGER;

function isRecord(value: unknown): value is Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function validateJson(value: unknown, path = "$"): asserts value is JsonValue {
  if (value === null || typeof value === "boolean" || typeof value === "string") return;
  if (typeof value === "number") {
    if (!Number.isSafeInteger(value)) {
      throw new ProtocolHelperError("INVALID_JSON_VALUE", `non-deterministic JSON number at ${path}`);
    }
    return;
  }
  if (Array.isArray(value)) {
    value.forEach((item, index) => validateJson(item, `${path}[${index}]`));
    return;
  }
  if (isRecord(value)) {
    for (const [key, item] of Object.entries(value)) validateJson(item, `${path}.${key}`);
    return;
  }
  throw new ProtocolHelperError("INVALID_JSON_VALUE", `unsupported JSON value at ${path}`);
}

function sortJson(value: JsonValue): JsonValue {
  if (Array.isArray(value)) return value.map(sortJson);
  if (isRecord(value)) {
    return Object.fromEntries(
      Object.keys(value).sort().map((key) => [key, sortJson(value[key] as JsonValue)]),
    );
  }
  return value;
}

export function deterministicJson(value: unknown): string {
  validateJson(value);
  return JSON.stringify(sortJson(value));
}

function detachedJson(value: unknown): JsonValue {
  return JSON.parse(deterministicJson(value)) as JsonValue;
}

export const MCP_CURRENT = "2026-07-28";
export const MCP_COMPATIBILITY = "2025-11-25";
export const MCP_SUPPORTED_VERSIONS = Object.freeze([MCP_CURRENT, MCP_COMPATIBILITY]);

const METHOD = /^[A-Za-z][A-Za-z0-9._-]*(?:\/[A-Za-z][A-Za-z0-9._-]*)*$/;
const SESSION_ID = /^[A-Za-z0-9._~-]{1,128}$/;
const DEPRECATED_PREFIXES = ["roots/", "sampling/", "logging/"];
const NAMED_METHOD_FIELDS: Readonly<Record<string, string>> = Object.freeze({
  "prompts/get": "name",
  "resources/read": "uri",
  "tools/call": "name",
});

function visibleAscii(value: unknown, field: string, maximum = 128): string {
  if (
    typeof value !== "string" || value.length < 1 || value.length > maximum ||
    [...value].some((character) => character.charCodeAt(0) < 0x20 || character.charCodeAt(0) > 0x7e)
  ) {
    throw new ProtocolHelperError("INVALID_MCP_REQUEST", `${field} must be bounded printable ASCII`);
  }
  return value;
}

export function negotiateMcpVersion(offered: readonly string[]): string {
  if (
    !Array.isArray(offered) || offered.length === 0 ||
    offered.some((version) => typeof version !== "string")
  ) {
    throw new ProtocolHelperError("UNSUPPORTED_PROTOCOL_VERSION", "MCP versions must be an ordered sequence");
  }
  if (offered.includes(MCP_CURRENT)) return MCP_CURRENT;
  if (offered.includes(MCP_COMPATIBILITY)) return MCP_COMPATIBILITY;
  throw new ProtocolHelperError("UNSUPPORTED_PROTOCOL_VERSION", "no admitted MCP revision was offered");
}

export interface McpRequestInput {
  version: string;
  requestId: string | number;
  method: string;
  params: Record<string, unknown>;
  clientName?: string;
  clientVersion?: string;
  clientCapabilities?: Record<string, unknown>;
  sessionId?: string;
}

export interface McpRequest {
  version: string;
  headers: Record<string, string>;
  body: { jsonrpc: "2.0"; id: string | number; method: string; params: JsonObject };
}

export function buildMcpRequest(input: McpRequestInput): McpRequest {
  if (!MCP_SUPPORTED_VERSIONS.includes(input.version)) {
    throw new ProtocolHelperError("UNSUPPORTED_PROTOCOL_VERSION", `unsupported MCP revision: ${input.version}`);
  }
  if (
    (typeof input.requestId !== "string" && typeof input.requestId !== "number") ||
    (typeof input.requestId === "number" && !Number.isSafeInteger(input.requestId))
  ) {
    throw new ProtocolHelperError("INVALID_MCP_REQUEST", "requestId must be a safe integer or string");
  }
  if (typeof input.requestId === "string") visibleAscii(input.requestId, "requestId");
  if (typeof input.method !== "string" || !METHOD.test(input.method)) {
    throw new ProtocolHelperError("INVALID_MCP_REQUEST", "method is not a valid MCP method name");
  }
  if (DEPRECATED_PREFIXES.some((prefix) => input.method.startsWith(prefix))) {
    throw new ProtocolHelperError("DEPRECATED_MCP_METHOD", `deprecated MCP method is not admitted: ${input.method}`);
  }
  if (!isRecord(input.params)) {
    throw new ProtocolHelperError("INVALID_MCP_REQUEST", "params must be a JSON object");
  }
  const detachedParams = detachedJson(input.params);
  if (!isRecord(detachedParams)) {
    throw new ProtocolHelperError("INVALID_MCP_REQUEST", "params must be a JSON object");
  }
  const params = detachedParams as JsonObject;
  const headers: Record<string, string> = {
    Accept: "application/json, text/event-stream",
    "Content-Type": "application/json",
    "MCP-Protocol-Version": input.version,
  };

  if (input.version === MCP_CURRENT) {
    if (input.method === "initialize" || input.method === "notifications/initialized") {
      throw new ProtocolHelperError("LEGACY_HANDSHAKE_FORBIDDEN", "2026-07-28 has no initialize handshake");
    }
    if (input.sessionId !== undefined) {
      throw new ProtocolHelperError("MCP_SESSION_FORBIDDEN", "2026-07-28 requests are session-free");
    }
    if ("_meta" in params) {
      throw new ProtocolHelperError("INVALID_MCP_REQUEST", "caller-supplied _meta would shadow protocol identity");
    }
    const capabilities = detachedJson(input.clientCapabilities ?? {});
    if (!isRecord(capabilities)) {
      throw new ProtocolHelperError("INVALID_MCP_REQUEST", "clientCapabilities must be a JSON object");
    }
    params._meta = {
      "io.modelcontextprotocol/clientCapabilities": capabilities as JsonObject,
      "io.modelcontextprotocol/clientInfo": {
        name: visibleAscii(input.clientName, "clientName"),
        version: visibleAscii(input.clientVersion, "clientVersion"),
      },
      "io.modelcontextprotocol/protocolVersion": MCP_CURRENT,
    };
    headers["Mcp-Method"] = input.method;
    const nameField = NAMED_METHOD_FIELDS[input.method];
    if (nameField !== undefined) {
      if (!(nameField in params)) {
        throw new ProtocolHelperError("MCP_NAME_REQUIRED", `${input.method} requires params.${nameField}`);
      }
      headers["Mcp-Name"] = visibleAscii(params[nameField], `params.${nameField}`, 1024);
    }
  } else {
    if (
      input.clientName !== undefined || input.clientVersion !== undefined ||
      input.clientCapabilities !== undefined
    ) {
      throw new ProtocolHelperError("INVALID_MCP_REQUEST", "2025 compatibility identity is established by initialize");
    }
    if (input.method === "initialize" || input.method === "notifications/initialized") {
      throw new ProtocolHelperError("LEGACY_HANDSHAKE_EXTERNAL", "the compatibility helper does not own legacy initialization");
    }
    if (typeof input.sessionId !== "string" || !SESSION_ID.test(input.sessionId)) {
      throw new ProtocolHelperError("LEGACY_SESSION_REQUIRED", "2025-11-25 requests require an admitted session id");
    }
    headers["Mcp-Session-Id"] = input.sessionId;
  }
  return {
    body: { id: input.requestId, jsonrpc: "2.0", method: input.method, params },
    headers,
    version: input.version,
  };
}

export interface TaskClassification {
  state: string;
  phase: "ACTIVE" | "INTERRUPTED" | "TERMINAL";
  terminal: boolean;
  interrupted: boolean;
  successful: boolean | null;
}

const MCP_TASK_STATES: Readonly<Record<string, readonly [TaskClassification["phase"], boolean, boolean, boolean | null]>> = Object.freeze({
  working: ["ACTIVE", false, false, null],
  input_required: ["INTERRUPTED", false, true, null],
  completed: ["TERMINAL", true, false, true],
  failed: ["TERMINAL", true, false, false],
  cancelled: ["TERMINAL", true, false, false],
});

const A2A_TASK_STATES: Readonly<Record<string, readonly [TaskClassification["phase"], boolean, boolean, boolean | null]>> = Object.freeze({
  TASK_STATE_SUBMITTED: ["ACTIVE", false, false, null],
  TASK_STATE_WORKING: ["ACTIVE", false, false, null],
  TASK_STATE_COMPLETED: ["TERMINAL", true, false, true],
  TASK_STATE_FAILED: ["TERMINAL", true, false, false],
  TASK_STATE_CANCELED: ["TERMINAL", true, false, false],
  TASK_STATE_INPUT_REQUIRED: ["INTERRUPTED", false, true, null],
  TASK_STATE_REJECTED: ["TERMINAL", true, false, false],
  TASK_STATE_AUTH_REQUIRED: ["INTERRUPTED", false, true, null],
});

function classifyTaskState(
  state: unknown,
  admitted: Readonly<Record<string, readonly [TaskClassification["phase"], boolean, boolean, boolean | null]>>,
  code: string,
): TaskClassification {
  if (typeof state !== "string" || !(state in admitted)) {
    throw new ProtocolHelperError(code, `unsupported task state: ${String(state)}`);
  }
  const [phase, terminal, interrupted, successful] = admitted[state];
  return { interrupted, phase, state, successful, terminal };
}

export function classifyMcpTaskState(state: unknown): TaskClassification {
  return classifyTaskState(state, MCP_TASK_STATES, "INVALID_MCP_TASK_STATE");
}

export function classifyA2aTaskState(state: unknown): TaskClassification {
  return classifyTaskState(state, A2A_TASK_STATES, "INVALID_A2A_TASK_STATE");
}

export function buildSseResumeHeaders(lastEventId: unknown): Record<string, string> {
  if (
    typeof lastEventId !== "string" || lastEventId.length < 1 || lastEventId.length > 256 ||
    [...lastEventId].some((character) => character.charCodeAt(0) < 0x20 || character.charCodeAt(0) > 0x7e)
  ) {
    throw new ProtocolHelperError(
      "UNSAFE_RESUME_CURSOR",
      "Last-Event-ID must contain 1-256 printable ASCII characters",
    );
  }
  return { Accept: "text/event-stream", "Last-Event-ID": lastEventId };
}

const TOP_FIELDS = new Set([
  "data", "datacontenttype", "dataschema", "id", "organizationid", "partitionkey",
  "sequence", "source", "specversion", "subject", "time", "type",
]);
const DATA_FIELDS = new Set([
  "schemaVersion", "aggregateKind", "aggregateId", "aggregateVersion", "actor",
  "correlationId", "causationId", "reasonCode", "transition", "resourceRefs", "evidenceRefs",
]);
const EVENT_TYPES: Readonly<Record<string, readonly [string | ReadonlySet<string>, boolean]>> = Object.freeze({
  "harness.approval.state.changed.v1": ["ApprovalRequest", false],
  "harness.bundle-release.state.changed.v1": ["BundleRelease", false],
  "harness.evidence.state.changed.v1": ["EvidenceRecord", false],
  "harness.installation.state.changed.v1": ["HarnessInstallation", false],
  "harness.operation.state.changed.v1": ["Operation", false],
  "harness.policy-bundle.state.changed.v1": ["PolicyBundle", false],
  "harness.status.projection.updated.v1": [
    new Set(["TenantHarnessOverview", "PlaneStatusProjection", "HarnessStatusProjection"]), true,
  ],
});
const STABLE_ID = /^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)+$/;
const STATE = /^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*$/;
const UUID4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const DIGEST = /^sha256:[0-9a-f]{64}$/;
const SOURCE = /^urn:planeon:harness:[a-z][a-z0-9]*(?:[.-][a-z0-9]+)+$/;
const TIMESTAMP = /^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$/;

function cloudFail(message: string): never {
  throw new ProtocolHelperError("MALFORMED_CLOUD_EVENT", message);
}

function closedObject(value: unknown, fields: ReadonlySet<string>, context: string): Record<string, unknown> {
  if (!isRecord(value)) cloudFail(`${context} must be an object`);
  const keys = Object.keys(value);
  if (keys.length !== fields.size || keys.some((key) => !fields.has(key))) {
    cloudFail(`${context} fields are closed`);
  }
  return value;
}

function requirePattern(value: unknown, pattern: RegExp, context: string): string {
  if (typeof value !== "string" || !pattern.test(value)) cloudFail(`${context} is invalid`);
  return value;
}

function requireStableId(value: unknown, context: string): string {
  const result = requirePattern(value, STABLE_ID, context);
  if (result.length > 128) cloudFail(`${context} exceeds the stable identifier limit`);
  return result;
}

function requireTimestamp(value: unknown, context: string): void {
  const text = requirePattern(value, TIMESTAMP, context);
  const parsed = new Date(text);
  if (Number.isNaN(parsed.valueOf()) || parsed.toISOString().replace(".000Z", "Z") !== text) {
    cloudFail(`${context} is not a calendar timestamp`);
  }
}

function requireReferences(value: unknown, context: string): void {
  if (!Array.isArray(value)) cloudFail(`${context} must be an array`);
  const seen = new Set<string>();
  value.forEach((item, index) => {
    const reference = closedObject(item, new Set(["kind", "id", "digest"]), `${context}[${index}]`);
    requireStableId(reference.kind, `${context}[${index}].kind`);
    requireStableId(reference.id, `${context}[${index}].id`);
    requirePattern(reference.digest, DIGEST, `${context}[${index}].digest`);
    const encoded = deterministicJson(reference);
    if (seen.has(encoded)) cloudFail(`${context} contains duplicate references`);
    seen.add(encoded);
  });
}

export function validateHarnessCloudEvent(value: unknown): JsonObject {
  const event = closedObject(value, TOP_FIELDS, "HarnessCloudEvent");
  if (event.specversion !== "1.0" || event.datacontenttype !== "application/json") {
    cloudFail("CloudEvents version or content type is invalid");
  }
  if (event.dataschema !== "https://harness.planeon.ai/schemas/v1alpha1/events/harness-cloud-event.schema.json") {
    cloudFail("dataschema is not the pinned HarnessCloudEvent contract");
  }
  requirePattern(event.id, UUID4, "id");
  requirePattern(event.source, SOURCE, "source");
  requireStableId(event.subject, "subject");
  requireStableId(event.organizationid, "organizationid");
  requireStableId(event.partitionkey, "partitionkey");
  requireTimestamp(event.time, "time");
  if (!Number.isSafeInteger(event.sequence) || (event.sequence as number) < 1) {
    cloudFail("sequence must be a positive safe integer");
  }
  if (typeof event.type !== "string" || !(event.type in EVENT_TYPES)) cloudFail("event type is not admitted");

  const data = closedObject(event.data, DATA_FIELDS, "data");
  if (data.schemaVersion !== "harness.planeon.ai/event-data/v1alpha1") cloudFail("data.schemaVersion is invalid");
  requireStableId(data.aggregateId, "data.aggregateId");
  if (!Number.isSafeInteger(data.aggregateVersion) || (data.aggregateVersion as number) < 1) {
    cloudFail("data.aggregateVersion must be a positive safe integer");
  }
  const actor = closedObject(data.actor, new Set(["type", "id"]), "data.actor");
  if (!["HUMAN", "WORKLOAD", "SYSTEM", "TENANT"].includes(String(actor.type))) cloudFail("data.actor.type is invalid");
  requireStableId(actor.id, "data.actor.id");
  requirePattern(data.correlationId, UUID4, "data.correlationId");
  if (data.causationId !== null) requirePattern(data.causationId, UUID4, "data.causationId");
  requirePattern(data.reasonCode, STATE, "data.reasonCode");
  if (data.transition !== null) {
    const transition = closedObject(data.transition, new Set(["from", "to"]), "data.transition");
    requirePattern(transition.from, STATE, "data.transition.from");
    requirePattern(transition.to, STATE, "data.transition.to");
  }
  requireReferences(data.resourceRefs, "data.resourceRefs");
  requireReferences(data.evidenceRefs, "data.evidenceRefs");

  const [aggregateRequirement, transitionMustBeNull] = EVENT_TYPES[event.type as string];
  if (
    (typeof aggregateRequirement === "string" && data.aggregateKind !== aggregateRequirement) ||
    (aggregateRequirement instanceof Set && !aggregateRequirement.has(String(data.aggregateKind)))
  ) cloudFail("event type and aggregate kind differ");
  if (transitionMustBeNull && data.transition !== null) cloudFail("status projection events cannot carry a transition");
  if (!transitionMustBeNull && !isRecord(data.transition)) cloudFail("state-change events require a transition");
  return detachedJson(event) as JsonObject;
}

export function serializeHarnessCloudEvent(value: unknown): string {
  return deterministicJson(validateHarnessCloudEvent(value));
}
