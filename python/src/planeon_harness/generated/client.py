"""Generated transport-neutral request builders. Do not edit by hand."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final
from urllib.parse import quote

from .models import JsonValue

@dataclass(frozen=True, slots=True)
class Request:
    operation_id: str
    method: str
    path: str
    query: tuple[tuple[str, str], ...]
    headers: tuple[tuple[str, str], ...]
    body: Mapping[str, JsonValue] | None

OPERATIONS: Final[dict[str, dict[str, object]]] = {'getApprovalRequest': {'api': 'control-plane', 'method': 'GET', 'path': '/api/v1alpha1/approvals/{approvalId}', 'parameters': [{'wireName': 'approvalId', 'variableName': 'approval_id', 'location': 'path', 'required': True, 'valueType': 'str'}], 'requestBodyRequired': False, 'requestSchemaRef': None, 'responseSchemaRef': '../schemas/v1alpha1/lifecycle/approval-request.schema.json'}, 'getBundleRelease': {'api': 'distribution', 'method': 'GET', 'path': '/api/v1alpha1/releases/{releaseId}', 'parameters': [{'wireName': 'releaseId', 'variableName': 'release_id', 'location': 'path', 'required': True, 'valueType': 'str'}], 'requestBodyRequired': False, 'requestSchemaRef': None, 'responseSchemaRef': '../schemas/v1alpha1/lifecycle/bundle-release.schema.json'}, 'getEvidenceRecord': {'api': 'trust', 'method': 'GET', 'path': '/api/v1alpha1/evidence/{evidenceId}', 'parameters': [{'wireName': 'evidenceId', 'variableName': 'evidence_id', 'location': 'path', 'required': True, 'valueType': 'str'}], 'requestBodyRequired': False, 'requestSchemaRef': None, 'responseSchemaRef': '../schemas/v1alpha1/lifecycle/evidence-record.schema.json'}, 'getHarnessInstallation': {'api': 'operator', 'method': 'GET', 'path': '/api/v1alpha1/installations/{installationId}', 'parameters': [{'wireName': 'installationId', 'variableName': 'installation_id', 'location': 'path', 'required': True, 'valueType': 'str'}], 'requestBodyRequired': False, 'requestSchemaRef': None, 'responseSchemaRef': '../schemas/v1alpha1/lifecycle/harness-installation.schema.json'}, 'getOperation': {'api': 'control-plane', 'method': 'GET', 'path': '/api/v1alpha1/operations/{operationId}', 'parameters': [{'wireName': 'operationId', 'variableName': 'operation_id', 'location': 'path', 'required': True, 'valueType': 'str'}], 'requestBodyRequired': False, 'requestSchemaRef': None, 'responseSchemaRef': '../schemas/v1alpha1/lifecycle/operation.schema.json'}, 'getOperatorOrganizationHarnessOverview': {'api': 'status', 'method': 'GET', 'path': '/api/v1alpha1/organizations/{organizationId}/overview', 'parameters': [{'wireName': 'organizationId', 'variableName': 'organization_id', 'location': 'path', 'required': True, 'valueType': 'str'}], 'requestBodyRequired': False, 'requestSchemaRef': None, 'responseSchemaRef': '../schemas/v1alpha1/status/tenant-harness-overview.schema.json'}, 'getTenantHarnessOverview': {'api': 'status', 'method': 'GET', 'path': '/api/v1alpha1/overview', 'parameters': [], 'requestBodyRequired': False, 'requestSchemaRef': None, 'responseSchemaRef': '../schemas/v1alpha1/status/tenant-harness-overview.schema.json'}, 'getTenantHarnessStatus': {'api': 'status', 'method': 'GET', 'path': '/api/v1alpha1/harnesses/{harnessId}', 'parameters': [{'wireName': 'harnessId', 'variableName': 'harness_id', 'location': 'path', 'required': True, 'valueType': 'str'}], 'requestBodyRequired': False, 'requestSchemaRef': None, 'responseSchemaRef': '../schemas/v1alpha1/status/harness-status-projection.schema.json'}, 'getTenantPlaneStatus': {'api': 'status', 'method': 'GET', 'path': '/api/v1alpha1/planes/{planeId}', 'parameters': [{'wireName': 'planeId', 'variableName': 'plane_id', 'location': 'path', 'required': True, 'valueType': 'str'}], 'requestBodyRequired': False, 'requestSchemaRef': None, 'responseSchemaRef': '../schemas/v1alpha1/status/plane-status-projection.schema.json'}, 'listOrganizationHarnessPortfolio': {'api': 'status', 'method': 'GET', 'path': '/api/v1alpha1/organizations', 'parameters': [{'wireName': 'cursor', 'variableName': 'cursor', 'location': 'query', 'required': False, 'valueType': 'str'}, {'wireName': 'limit', 'variableName': 'limit', 'location': 'query', 'required': False, 'valueType': 'int'}, {'wireName': 'state', 'variableName': 'state', 'location': 'query', 'required': False, 'valueType': 'str'}], 'requestBodyRequired': False, 'requestSchemaRef': None, 'responseSchemaRef': '../schemas/v1alpha1/status/organization-harness-portfolio-page.schema.json'}, 'recordApprovalDecision': {'api': 'control-plane', 'method': 'POST', 'path': '/api/v1alpha1/approvals/{approvalId}/decision', 'parameters': [{'wireName': 'Idempotency-Key', 'variableName': 'idempotency_key', 'location': 'header', 'required': True, 'valueType': 'str'}, {'wireName': 'If-Match', 'variableName': 'if_match', 'location': 'header', 'required': True, 'valueType': 'str'}, {'wireName': 'approvalId', 'variableName': 'approval_id', 'location': 'path', 'required': True, 'valueType': 'str'}], 'requestBodyRequired': True, 'requestSchemaRef': '#/components/schemas/ApprovalDecision', 'responseSchemaRef': '../schemas/v1alpha1/lifecycle/operation.schema.json'}}

def build_request(
    operation_id: str,
    parameters: Mapping[str, str | int | bool | None],
    body: Mapping[str, JsonValue] | None = None,
) -> Request:
    try:
        operation = OPERATIONS[operation_id]
    except KeyError as exc:
        raise ValueError(f'unknown operation: {operation_id}') from exc
    specs = operation['parameters']
    assert isinstance(specs, list)
    admitted = {spec['variableName'] for spec in specs}
    unknown = sorted(set(parameters) - admitted)
    if unknown:
        raise ValueError(f'unknown operation parameter: {unknown[0]}')
    path = str(operation['path'])
    query: list[tuple[str, str]] = []
    headers: list[tuple[str, str]] = []
    for spec in specs:
        variable = str(spec['variableName'])
        value = parameters.get(variable)
        if value is None:
            if spec['required']:
                raise ValueError(f'missing operation parameter: {variable}')
            continue
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        location = spec['location']
        wire_name = str(spec['wireName'])
        if location == 'path':
            path = path.replace('{' + wire_name + '}', quote(rendered, safe=''))
        elif location == 'query':
            query.append((wire_name, rendered))
        elif location == 'header':
            headers.append((wire_name, rendered))
    if '{' in path or '}' in path:
        raise ValueError('not all path parameters were resolved')
    if operation['requestBodyRequired'] and body is None:
        raise ValueError('request body is required')
    if body is not None:
        headers.append(('Content-Type', 'application/json'))
    return Request(
        operation_id=operation_id,
        method=str(operation['method']),
        path=path,
        query=tuple(query),
        headers=tuple(headers),
        body=body,
    )

class HarnessClient:
    """Build requests for a caller-supplied transport; performs no I/O."""

    def get_approval_request(self, *, approval_id: str) -> Request:
        parameters = {'approval_id': approval_id}
        return build_request('getApprovalRequest', parameters)

    def get_bundle_release(self, *, release_id: str) -> Request:
        parameters = {'release_id': release_id}
        return build_request('getBundleRelease', parameters)

    def get_evidence_record(self, *, evidence_id: str) -> Request:
        parameters = {'evidence_id': evidence_id}
        return build_request('getEvidenceRecord', parameters)

    def get_harness_installation(self, *, installation_id: str) -> Request:
        parameters = {'installation_id': installation_id}
        return build_request('getHarnessInstallation', parameters)

    def get_operation(self, *, operation_id: str) -> Request:
        parameters = {'operation_id': operation_id}
        return build_request('getOperation', parameters)

    def get_operator_organization_harness_overview(self, *, organization_id: str) -> Request:
        parameters = {'organization_id': organization_id}
        return build_request('getOperatorOrganizationHarnessOverview', parameters)

    def get_tenant_harness_overview(self) -> Request:
        parameters = {}
        return build_request('getTenantHarnessOverview', parameters)

    def get_tenant_harness_status(self, *, harness_id: str) -> Request:
        parameters = {'harness_id': harness_id}
        return build_request('getTenantHarnessStatus', parameters)

    def get_tenant_plane_status(self, *, plane_id: str) -> Request:
        parameters = {'plane_id': plane_id}
        return build_request('getTenantPlaneStatus', parameters)

    def list_organization_harness_portfolio(self, *, cursor: str | None = None, limit: int | None = None, state: str | None = None) -> Request:
        parameters = {'cursor': cursor, 'limit': limit, 'state': state}
        return build_request('listOrganizationHarnessPortfolio', parameters)

    def record_approval_decision(self, *, idempotency_key: str, if_match: str, approval_id: str, body: Mapping[str, JsonValue]) -> Request:
        parameters = {'idempotency_key': idempotency_key, 'if_match': if_match, 'approval_id': approval_id}
        return build_request('recordApprovalDecision', parameters, body)
