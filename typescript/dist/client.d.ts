// Generated client declarations. Do not edit by hand.
import type { JsonObject } from './models.js';

export interface RequestSpec {
  readonly operationId: string;
  readonly method: string;
  readonly path: string;
  readonly query: ReadonlyArray<readonly [string, string]>;
  readonly headers: ReadonlyArray<readonly [string, string]>;
  readonly body?: JsonObject;
}
export declare const OPERATIONS: Readonly<Record<string, {
  readonly api: string;
  readonly method: string;
  readonly path: string;
  readonly parameters: ReadonlyArray<{
    readonly wireName: string;
    readonly variableName: string;
    readonly location: 'header' | 'path' | 'query';
    readonly required: boolean;
    readonly valueType: 'str' | 'int' | 'bool';
  }>;
  readonly requestBodyRequired: boolean;
  readonly requestSchemaRef: string | null;
  readonly responseSchemaRef: string | null;
}>>;
export type OperationId = keyof typeof OPERATIONS;
export declare function buildRequest(
  operationId: OperationId,
  parameters: Readonly<Record<string, string | number | boolean | undefined>>,
  body?: JsonObject,
): RequestSpec;

export declare function getApprovalRequest(args: { approvalId: string }): RequestSpec;
export declare function getBundleRelease(args: { releaseId: string }): RequestSpec;
export declare function getEvidenceRecord(args: { evidenceId: string }): RequestSpec;
export declare function getHarnessInstallation(args: { installationId: string }): RequestSpec;
export declare function getOperation(args: { operationId: string }): RequestSpec;
export declare function getOperatorOrganizationHarnessOverview(args: { organizationId: string }): RequestSpec;
export declare function getTenantHarnessOverview(): RequestSpec;
export declare function getTenantHarnessStatus(args: { harnessId: string }): RequestSpec;
export declare function getTenantPlaneStatus(args: { planeId: string }): RequestSpec;
export declare function listOrganizationHarnessPortfolio(args: { cursor?: string; limit?: number; state?: string }): RequestSpec;
export declare function recordApprovalDecision(args: { idempotencyKey: string; ifMatch: string; approvalId: string; body: JsonObject }): RequestSpec;
