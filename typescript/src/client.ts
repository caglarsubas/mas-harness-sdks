// Generated transport-neutral request builders. Do not edit by hand.
import type { JsonObject, JsonValue } from './models.js';

export interface RequestSpec {
  readonly operationId: string;
  readonly method: string;
  readonly path: string;
  readonly query: ReadonlyArray<readonly [string, string]>;
  readonly headers: ReadonlyArray<readonly [string, string]>;
  readonly body?: JsonObject;
}

export const OPERATIONS = {"getApprovalRequest":{"api":"control-plane","method":"GET","parameters":[{"location":"path","required":true,"valueType":"str","variableName":"approval_id","wireName":"approvalId"}],"path":"/api/v1alpha1/approvals/{approvalId}","requestBodyRequired":false,"requestSchemaRef":null,"responseSchemaRef":"../schemas/v1alpha1/lifecycle/approval-request.schema.json"},"getBundleRelease":{"api":"distribution","method":"GET","parameters":[{"location":"path","required":true,"valueType":"str","variableName":"release_id","wireName":"releaseId"}],"path":"/api/v1alpha1/releases/{releaseId}","requestBodyRequired":false,"requestSchemaRef":null,"responseSchemaRef":"../schemas/v1alpha1/lifecycle/bundle-release.schema.json"},"getEvidenceRecord":{"api":"trust","method":"GET","parameters":[{"location":"path","required":true,"valueType":"str","variableName":"evidence_id","wireName":"evidenceId"}],"path":"/api/v1alpha1/evidence/{evidenceId}","requestBodyRequired":false,"requestSchemaRef":null,"responseSchemaRef":"../schemas/v1alpha1/lifecycle/evidence-record.schema.json"},"getHarnessInstallation":{"api":"operator","method":"GET","parameters":[{"location":"path","required":true,"valueType":"str","variableName":"installation_id","wireName":"installationId"}],"path":"/api/v1alpha1/installations/{installationId}","requestBodyRequired":false,"requestSchemaRef":null,"responseSchemaRef":"../schemas/v1alpha1/lifecycle/harness-installation.schema.json"},"getOperation":{"api":"control-plane","method":"GET","parameters":[{"location":"path","required":true,"valueType":"str","variableName":"operation_id","wireName":"operationId"}],"path":"/api/v1alpha1/operations/{operationId}","requestBodyRequired":false,"requestSchemaRef":null,"responseSchemaRef":"../schemas/v1alpha1/lifecycle/operation.schema.json"},"getOperatorOrganizationHarnessOverview":{"api":"status","method":"GET","parameters":[{"location":"path","required":true,"valueType":"str","variableName":"organization_id","wireName":"organizationId"}],"path":"/api/v1alpha1/organizations/{organizationId}/overview","requestBodyRequired":false,"requestSchemaRef":null,"responseSchemaRef":"../schemas/v1alpha1/status/tenant-harness-overview.schema.json"},"getTenantHarnessOverview":{"api":"status","method":"GET","parameters":[],"path":"/api/v1alpha1/overview","requestBodyRequired":false,"requestSchemaRef":null,"responseSchemaRef":"../schemas/v1alpha1/status/tenant-harness-overview.schema.json"},"getTenantHarnessStatus":{"api":"status","method":"GET","parameters":[{"location":"path","required":true,"valueType":"str","variableName":"harness_id","wireName":"harnessId"}],"path":"/api/v1alpha1/harnesses/{harnessId}","requestBodyRequired":false,"requestSchemaRef":null,"responseSchemaRef":"../schemas/v1alpha1/status/harness-status-projection.schema.json"},"getTenantPlaneStatus":{"api":"status","method":"GET","parameters":[{"location":"path","required":true,"valueType":"str","variableName":"plane_id","wireName":"planeId"}],"path":"/api/v1alpha1/planes/{planeId}","requestBodyRequired":false,"requestSchemaRef":null,"responseSchemaRef":"../schemas/v1alpha1/status/plane-status-projection.schema.json"},"listOrganizationHarnessPortfolio":{"api":"status","method":"GET","parameters":[{"location":"query","required":false,"valueType":"str","variableName":"cursor","wireName":"cursor"},{"location":"query","required":false,"valueType":"int","variableName":"limit","wireName":"limit"},{"location":"query","required":false,"valueType":"str","variableName":"state","wireName":"state"}],"path":"/api/v1alpha1/organizations","requestBodyRequired":false,"requestSchemaRef":null,"responseSchemaRef":"../schemas/v1alpha1/status/organization-harness-portfolio-page.schema.json"},"recordApprovalDecision":{"api":"control-plane","method":"POST","parameters":[{"location":"header","required":true,"valueType":"str","variableName":"idempotency_key","wireName":"Idempotency-Key"},{"location":"header","required":true,"valueType":"str","variableName":"if_match","wireName":"If-Match"},{"location":"path","required":true,"valueType":"str","variableName":"approval_id","wireName":"approvalId"}],"path":"/api/v1alpha1/approvals/{approvalId}/decision","requestBodyRequired":true,"requestSchemaRef":"#/components/schemas/ApprovalDecision","responseSchemaRef":"../schemas/v1alpha1/lifecycle/operation.schema.json"}} as const;
export type OperationId = keyof typeof OPERATIONS;

export function buildRequest(
  operationId: OperationId,
  parameters: Readonly<Record<string, string | number | boolean | undefined>>,
  body?: JsonObject,
): RequestSpec {
  const operation = OPERATIONS[operationId];
  const admitted = new Set(operation.parameters.map((parameter) => parameter.variableName));
  const unknown = Object.keys(parameters).filter((name) => !admitted.has(name));
  if (unknown.length > 0) throw new Error(`unknown operation parameter: ${unknown.sort()[0]}`);
  let path = operation.path;
  const query: Array<readonly [string, string]> = [];
  const headers: Array<readonly [string, string]> = [];
  for (const parameter of operation.parameters) {
    const value = parameters[parameter.variableName];
    if (value === undefined) {
      if (parameter.required) throw new Error(`missing operation parameter: ${parameter.variableName}`);
      continue;
    }
    const rendered = String(value);
    if (parameter.location === 'path') path = path.replace(`{${parameter.wireName}}`, encodeURIComponent(rendered));
    if (parameter.location === 'query') query.push([parameter.wireName, rendered]);
    if (parameter.location === 'header') headers.push([parameter.wireName, rendered]);
  }
  if (path.includes('{') || path.includes('}')) throw new Error('not all path parameters were resolved');
  if (operation.requestBodyRequired && body === undefined) throw new Error('request body is required');
  if (body !== undefined) headers.push(['Content-Type', 'application/json']);
  return { operationId, method: operation.method, path, query, headers, ...(body === undefined ? {} : { body }) };
}

export function getApprovalRequest(args: { approvalId: string }): RequestSpec {
  return buildRequest("getApprovalRequest", { "approval_id": args.approvalId });
}

export function getBundleRelease(args: { releaseId: string }): RequestSpec {
  return buildRequest("getBundleRelease", { "release_id": args.releaseId });
}

export function getEvidenceRecord(args: { evidenceId: string }): RequestSpec {
  return buildRequest("getEvidenceRecord", { "evidence_id": args.evidenceId });
}

export function getHarnessInstallation(args: { installationId: string }): RequestSpec {
  return buildRequest("getHarnessInstallation", { "installation_id": args.installationId });
}

export function getOperation(args: { operationId: string }): RequestSpec {
  return buildRequest("getOperation", { "operation_id": args.operationId });
}

export function getOperatorOrganizationHarnessOverview(args: { organizationId: string }): RequestSpec {
  return buildRequest("getOperatorOrganizationHarnessOverview", { "organization_id": args.organizationId });
}

export function getTenantHarnessOverview(): RequestSpec {
  return buildRequest("getTenantHarnessOverview", {  });
}

export function getTenantHarnessStatus(args: { harnessId: string }): RequestSpec {
  return buildRequest("getTenantHarnessStatus", { "harness_id": args.harnessId });
}

export function getTenantPlaneStatus(args: { planeId: string }): RequestSpec {
  return buildRequest("getTenantPlaneStatus", { "plane_id": args.planeId });
}

export function listOrganizationHarnessPortfolio(args: { cursor?: string; limit?: number; state?: string }): RequestSpec {
  return buildRequest("listOrganizationHarnessPortfolio", { "cursor": args.cursor, "limit": args.limit, "state": args.state });
}

export function recordApprovalDecision(args: { idempotencyKey: string; ifMatch: string; approvalId: string; body: JsonObject }): RequestSpec {
  return buildRequest("recordApprovalDecision", { "idempotency_key": args.idempotencyKey, "if_match": args.ifMatch, "approval_id": args.approvalId }, args.body);
}
