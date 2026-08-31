export type JsonPrimitive = null | boolean | number | string;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };
export type JsonObject = { [key: string]: JsonValue };
export declare class ProtocolHelperError extends Error {
  readonly code: string;
  constructor(code: string, message: string);
}
export declare function deterministicJson(value: unknown): string;
export declare const MCP_CURRENT = "2026-07-28";
export declare const MCP_COMPATIBILITY = "2025-11-25";
export declare const MCP_SUPPORTED_VERSIONS: readonly string[];
export declare function negotiateMcpVersion(offered: readonly string[]): string;
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
export declare function buildMcpRequest(input: McpRequestInput): McpRequest;
export interface TaskClassification {
  state: string;
  phase: "ACTIVE" | "INTERRUPTED" | "TERMINAL";
  terminal: boolean;
  interrupted: boolean;
  successful: boolean | null;
}
export declare function classifyMcpTaskState(state: unknown): TaskClassification;
export declare function classifyA2aTaskState(state: unknown): TaskClassification;
export declare function buildSseResumeHeaders(lastEventId: unknown): Record<string, string>;
export declare function validateHarnessCloudEvent(value: unknown): JsonObject;
export declare function serializeHarnessCloudEvent(value: unknown): string;
