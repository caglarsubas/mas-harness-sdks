"""Generated contract models. Do not edit by hand."""

from __future__ import annotations

from typing import Final, Literal, TypeAlias, TypedDict

JsonScalar: TypeAlias = None | bool | int | float | str
JsonValue: TypeAlias = JsonScalar | list['JsonValue'] | dict[str, 'JsonValue']
CONTRACT_RELEASE_DIGEST: Final = 'sha256:76c6098ce16da7e5c45d7955feb65f4972715c803e4f989443def0edbca38105'

class ApprovalDecision(TypedDict):
    decision: Literal['APPROVE', 'REJECT']
    reasonCode: str

class ApprovalRequest(TypedDict):
    apiVersion: JsonValue
    kind: Literal['ApprovalRequest']
    metadata: JsonValue
    spec: dict[str, JsonValue]

class BillOfMaterials(TypedDict):
    apiVersion: JsonValue
    kind: Literal['BillOfMaterials']
    metadata: JsonValue
    spec: dict[str, JsonValue]

class BundleRelease(TypedDict):
    apiVersion: JsonValue
    kind: Literal['BundleRelease']
    metadata: JsonValue
    spec: dict[str, JsonValue]

class CompileRequest(TypedDict):
    demand: dict[str, JsonValue]
    metadata: dict[str, JsonValue]
    questionnaireAnswerSet: JsonValue
    readinessAssessment: JsonValue
    schemaVersion: Literal['harness.planeon.ai/compile-request/v1alpha1']

class CompiledProfileDocument(TypedDict):
    executionBudget: JsonValue
    profile: JsonValue
    schemaVersion: Literal['harness.planeon.ai/compiled-profile-document/v1alpha1']
    tenantDemand: JsonValue

class CompositionCommonSchemaApiVersion(TypedDict, total=False):
    pass

class CompositionCommonSchemaAssuranceSubjects(TypedDict):
    capabilityIds: list[JsonValue]
    harnessIds: list[JsonValue]

class CompositionCommonSchemaEnvironment(TypedDict):
    architecture: Literal['amd64', 'arm64', 'platform-supplied']
    attestationDigest: JsonValue
    capabilities: list[JsonValue]
    deploymentMode: Literal['operator-hosted-saas', 'tenant-public-cloud', 'self-managed', 'air-gapped']
    kubernetesDistribution: Literal['upstream', 'k3s', 'openshift', 'none', 'platform-supplied']
    operatingSystem: Literal['linux', 'macos', 'platform-supplied']
    signatureStatus: Literal['VERIFIED']
    tenantId: JsonValue

class CompositionCommonSchemaExecutionBudgetSpec(TypedDict):
    maxConcurrentTasks: int
    maxModelTokens: int
    maxRetries: int
    maxTaskSeconds: int
    maxToolCalls: int

class CompositionCommonSchemaInstallUnit(TypedDict):
    artifactName: JsonValue
    digest: None
    digestStatus: Literal['MISSING_PLANNED']
    id: JsonValue
    type: Literal['OCI_IMAGE', 'OCI_ARTIFACT', 'HELM_CHART', 'PYTHON_WHEEL', 'NPM_TARBALL', 'LOCAL_BINARY', 'KUBERNETES_RUNTIME_CLASS', 'TENANT_SUPPLIED_PLATFORM']

class CompositionCommonSchemaMetadata(TypedDict):
    id: JsonValue
    version: JsonValue

class CompositionCommonSchemaProviderSelection(TypedDict):
    groupId: JsonValue
    providerId: JsonValue
    selectorCapability: JsonValue

class CompositionCommonSchemaSelectorProposal(TypedDict):
    disposition: Literal['PROPOSED_SELECTOR_ONLY']
    groupId: JsonValue
    selectorCapabilities: list[JsonValue]

class CompositionCommonSchemaSemver(TypedDict, total=False):
    pass

class CompositionCommonSchemaSha256(TypedDict, total=False):
    pass

class CompositionCommonSchemaStableId(TypedDict, total=False):
    pass

class EvidencePlan(TypedDict):
    apiVersion: JsonValue
    kind: Literal['EvidencePlan']
    metadata: JsonValue
    spec: dict[str, JsonValue]

class EvidenceRecord(TypedDict):
    apiVersion: JsonValue
    kind: Literal['EvidenceRecord']
    metadata: JsonValue
    spec: dict[str, JsonValue]

class ExecutionBudget(TypedDict):
    apiVersion: JsonValue
    kind: Literal['ExecutionBudget']
    metadata: JsonValue
    spec: dict[str, JsonValue]

class HarnessCloudEvent(TypedDict):
    data: dict[str, JsonValue]
    datacontenttype: Literal['application/json']
    dataschema: Literal['https://harness.planeon.ai/schemas/v1alpha1/events/harness-cloud-event.schema.json']
    id: str
    organizationid: JsonValue
    partitionkey: JsonValue
    sequence: int
    source: str
    specversion: Literal['1.0']
    subject: JsonValue
    time: JsonValue
    type: Literal['harness.approval.state.changed.v1', 'harness.bundle-release.state.changed.v1', 'harness.evidence.state.changed.v1', 'harness.installation.state.changed.v1', 'harness.operation.state.changed.v1', 'harness.policy-bundle.state.changed.v1', 'harness.status.projection.updated.v1']

class HarnessInstallation(TypedDict):
    apiVersion: JsonValue
    kind: Literal['HarnessInstallation']
    metadata: JsonValue
    spec: dict[str, JsonValue]

class HarnessProfile(TypedDict):
    apiVersion: JsonValue
    kind: Literal['HarnessProfile']
    metadata: JsonValue
    spec: dict[str, JsonValue]

class HarnessStatusProjection(TypedDict):
    apiVersion: JsonValue
    binding: JsonValue
    kind: Literal['HarnessStatusProjection']
    metadata: JsonValue
    spec: dict[str, JsonValue]

class InstallPlan(TypedDict):
    apiVersion: JsonValue
    kind: Literal['InstallPlan']
    metadata: JsonValue
    spec: dict[str, JsonValue]

class LifecycleCommonSchemaActor(TypedDict):
    id: JsonValue
    type: Literal['HUMAN', 'WORKLOAD', 'SYSTEM', 'TENANT']

class LifecycleCommonSchemaApiVersion(TypedDict, total=False):
    pass

class LifecycleCommonSchemaFailure(TypedDict):
    evidenceRefs: list[JsonValue]
    reasonCode: JsonValue
    retryable: bool

class LifecycleCommonSchemaImmutableBinding(TypedDict):
    bundleDigest: JsonValue
    organizationId: JsonValue
    profileDigest: JsonValue
    releaseDigest: JsonValue

class LifecycleCommonSchemaMetadata(TypedDict):
    id: JsonValue
    version: JsonValue

class LifecycleCommonSchemaReasonCode(TypedDict, total=False):
    pass

class LifecycleCommonSchemaResourceRef(TypedDict):
    digest: JsonValue
    id: JsonValue
    kind: JsonValue

class LifecycleCommonSchemaSemver(TypedDict, total=False):
    pass

class LifecycleCommonSchemaSha256(TypedDict, total=False):
    pass

class LifecycleCommonSchemaStableId(TypedDict, total=False):
    pass

class LifecycleCommonSchemaTimestamp(TypedDict, total=False):
    pass

class Operation(TypedDict):
    apiVersion: JsonValue
    kind: Literal['Operation']
    metadata: JsonValue
    spec: dict[str, JsonValue]

class OrganizationHarnessPortfolioPage(TypedDict):
    apiVersion: JsonValue
    kind: Literal['OrganizationHarnessPortfolioPage']
    metadata: JsonValue
    spec: dict[str, JsonValue]

class PlaneStatusProjection(TypedDict):
    apiVersion: JsonValue
    binding: JsonValue
    kind: Literal['PlaneStatusProjection']
    metadata: JsonValue
    spec: dict[str, JsonValue]

class PolicyBundle(TypedDict):
    apiVersion: JsonValue
    kind: Literal['PolicyBundle']
    metadata: JsonValue
    spec: dict[str, JsonValue]

class ProjectionFreshness(TypedDict):
    apiVersion: JsonValue
    binding: JsonValue
    kind: Literal['ProjectionFreshness']
    metadata: JsonValue
    spec: JsonValue

class StatusAxisProjection(TypedDict):
    apiVersion: JsonValue
    binding: JsonValue
    kind: Literal['StatusAxisProjection']
    metadata: JsonValue
    spec: JsonValue

class StatusCommonSchemaAggregateState(TypedDict, total=False):
    pass

class StatusCommonSchemaApiVersion(TypedDict, total=False):
    pass

class StatusCommonSchemaApplicability(TypedDict):
    contractRef: JsonValue
    reasonCode: JsonValue

class StatusCommonSchemaEvidenceAxis(TypedDict, total=False):
    pass

class StatusCommonSchemaEvidenceState(TypedDict, total=False):
    pass

class StatusCommonSchemaFinding(TypedDict):
    affectedAxis: JsonValue
    blocking: bool
    evidenceRefs: list[JsonValue]
    findingId: JsonValue
    ownerRef: JsonValue
    permittedActions: list[Literal['REQUEST_EVIDENCE', 'REFRESH_PROJECTION', 'REVIEW_WAIVER', 'RETRY_OPERATION', 'ROLLBACK', 'RESOLVE_DEPENDENCY', 'CONTACT_OWNER', 'NONE']]
    reasonCode: JsonValue
    severity: Literal['INFO', 'WARN', 'ERROR', 'CRITICAL']

class StatusCommonSchemaFreshness(TypedDict):
    freshUntil: JsonValue
    projectedAt: JsonValue
    sourceCursors: list[JsonValue]
    state: JsonValue

class StatusCommonSchemaFreshnessState(TypedDict, total=False):
    pass

class StatusCommonSchemaHarnessSummary(TypedDict):
    aggregateState: JsonValue
    blockerCount: int
    freshnessState: JsonValue
    harnessId: JsonValue
    highestEvidenceState: JsonValue
    installationState: JsonValue
    planeId: Literal['runtime', 'knowledge', 'execution', 'trust']
    reasonCode: JsonValue
    selectionState: JsonValue

class StatusCommonSchemaInstallationState(TypedDict, total=False):
    pass

class StatusCommonSchemaMetadata(TypedDict, total=False):
    pass

class StatusCommonSchemaNonWaivedEvidenceState(TypedDict, total=False):
    pass

class StatusCommonSchemaPlaneSummary(TypedDict):
    aggregateState: JsonValue
    blockingDependencyCount: int
    freshnessState: JsonValue
    harnesses: list[JsonValue]
    notSelectedCount: int
    planeId: Literal['runtime', 'knowledge', 'execution', 'trust']
    selectedCount: int
    worstInstallationState: JsonValue

class StatusCommonSchemaProjectionBinding(TypedDict):
    bundleDigest: JsonValue
    freshUntil: JsonValue
    observedGeneration: int
    organizationId: JsonValue
    profileDigest: JsonValue
    projectedAt: JsonValue
    projectionSchemaVersion: Literal['harness.planeon.ai/status-projection/v1alpha1']
    releaseDigest: JsonValue
    sourceCursors: list[JsonValue]

class StatusCommonSchemaReasonCode(TypedDict, total=False):
    pass

class StatusCommonSchemaResourceRef(TypedDict, total=False):
    pass

class StatusCommonSchemaSelectionState(TypedDict, total=False):
    pass

class StatusCommonSchemaSemver(TypedDict, total=False):
    pass

class StatusCommonSchemaSha256(TypedDict, total=False):
    pass

class StatusCommonSchemaSourceCursor(TypedDict):
    cursor: str
    observedAt: JsonValue
    sourceId: JsonValue
    state: Literal['CURRENT', 'SOURCE_UNAVAILABLE']

class StatusCommonSchemaStableId(TypedDict, total=False):
    pass

class StatusCommonSchemaStateCount(TypedDict):
    count: int
    state: str

class StatusCommonSchemaStatusAxis(TypedDict):
    applicability: JsonValue
    axis: JsonValue
    evidenceRefs: list[JsonValue]
    observedAt: JsonValue
    required: bool
    state: JsonValue
    underlyingState: JsonValue
    waiver: JsonValue

class StatusCommonSchemaTimestamp(TypedDict, total=False):
    pass

class StatusCommonSchemaWaiver(TypedDict):
    approvedBy: JsonValue
    basisCode: JsonValue
    expiresAt: JsonValue
    waiverDigest: JsonValue
    waiverId: JsonValue

class StatusFindingSummary(TypedDict):
    apiVersion: JsonValue
    binding: JsonValue
    kind: Literal['StatusFindingSummary']
    metadata: JsonValue
    spec: JsonValue

class TenantDemand(TypedDict):
    apiVersion: JsonValue
    kind: Literal['TenantDemand']
    metadata: JsonValue
    spec: dict[str, JsonValue]

class TenantHarnessOverview(TypedDict):
    apiVersion: JsonValue
    binding: JsonValue
    kind: Literal['TenantHarnessOverview']
    metadata: JsonValue
    spec: dict[str, JsonValue]

MODEL_CONTRACTS: Final[dict[str, dict[str, object]]] = {'ApprovalDecision': {'sourcePath': 'openapi/control-plane.openapi.json', 'schemaPointer': '/components/schemas/ApprovalDecision', 'schemaId': None, 'requiredFields': ['decision', 'reasonCode']}, 'ApprovalRequest': {'sourcePath': 'schemas/v1alpha1/lifecycle/approval-request.schema.json', 'schemaPointer': '', 'schemaId': 'https://harness.planeon.ai/schemas/v1alpha1/lifecycle/approval-request.schema.json', 'requiredFields': ['apiVersion', 'kind', 'metadata', 'spec']}, 'BillOfMaterials': {'sourcePath': 'schemas/v1alpha1/composition/bill-of-materials.schema.json', 'schemaPointer': '', 'schemaId': 'https://harness.planeon.ai/schemas/v1alpha1/composition/bill-of-materials.schema.json', 'requiredFields': ['apiVersion', 'kind', 'metadata', 'spec']}, 'BundleRelease': {'sourcePath': 'schemas/v1alpha1/lifecycle/bundle-release.schema.json', 'schemaPointer': '', 'schemaId': 'https://harness.planeon.ai/schemas/v1alpha1/lifecycle/bundle-release.schema.json', 'requiredFields': ['apiVersion', 'kind', 'metadata', 'spec']}, 'CompileRequest': {'sourcePath': 'schemas/v1alpha1/composition/compile-request.schema.json', 'schemaPointer': '', 'schemaId': 'https://harness.planeon.ai/schemas/v1alpha1/composition/compile-request.schema.json', 'requiredFields': ['demand', 'metadata', 'questionnaireAnswerSet', 'readinessAssessment', 'schemaVersion']}, 'CompiledProfileDocument': {'sourcePath': 'schemas/v1alpha1/composition/compiled-profile-document.schema.json', 'schemaPointer': '', 'schemaId': 'https://harness.planeon.ai/schemas/v1alpha1/composition/compiled-profile-document.schema.json', 'requiredFields': ['executionBudget', 'profile', 'schemaVersion', 'tenantDemand']}, 'CompositionCommonSchemaApiVersion': {'sourcePath': 'schemas/v1alpha1/composition/common.schema.json', 'schemaPointer': '/$defs/apiVersion', 'schemaId': None, 'requiredFields': []}, 'CompositionCommonSchemaAssuranceSubjects': {'sourcePath': 'schemas/v1alpha1/composition/common.schema.json', 'schemaPointer': '/$defs/assuranceSubjects', 'schemaId': None, 'requiredFields': ['capabilityIds', 'harnessIds']}, 'CompositionCommonSchemaEnvironment': {'sourcePath': 'schemas/v1alpha1/composition/common.schema.json', 'schemaPointer': '/$defs/environment', 'schemaId': None, 'requiredFields': ['architecture', 'attestationDigest', 'capabilities', 'deploymentMode', 'kubernetesDistribution', 'operatingSystem', 'signatureStatus', 'tenantId']}, 'CompositionCommonSchemaExecutionBudgetSpec': {'sourcePath': 'schemas/v1alpha1/composition/common.schema.json', 'schemaPointer': '/$defs/executionBudgetSpec', 'schemaId': None, 'requiredFields': ['maxConcurrentTasks', 'maxModelTokens', 'maxRetries', 'maxTaskSeconds', 'maxToolCalls']}, 'CompositionCommonSchemaInstallUnit': {'sourcePath': 'schemas/v1alpha1/composition/common.schema.json', 'schemaPointer': '/$defs/installUnit', 'schemaId': None, 'requiredFields': ['artifactName', 'digest', 'digestStatus', 'id', 'type']}, 'CompositionCommonSchemaMetadata': {'sourcePath': 'schemas/v1alpha1/composition/common.schema.json', 'schemaPointer': '/$defs/metadata', 'schemaId': None, 'requiredFields': ['id', 'version']}, 'CompositionCommonSchemaProviderSelection': {'sourcePath': 'schemas/v1alpha1/composition/common.schema.json', 'schemaPointer': '/$defs/providerSelection', 'schemaId': None, 'requiredFields': ['groupId', 'providerId', 'selectorCapability']}, 'CompositionCommonSchemaSelectorProposal': {'sourcePath': 'schemas/v1alpha1/composition/common.schema.json', 'schemaPointer': '/$defs/selectorProposal', 'schemaId': None, 'requiredFields': ['disposition', 'groupId', 'selectorCapabilities']}, 'CompositionCommonSchemaSemver': {'sourcePath': 'schemas/v1alpha1/composition/common.schema.json', 'schemaPointer': '/$defs/semver', 'schemaId': None, 'requiredFields': []}, 'CompositionCommonSchemaSha256': {'sourcePath': 'schemas/v1alpha1/composition/common.schema.json', 'schemaPointer': '/$defs/sha256', 'schemaId': None, 'requiredFields': []}, 'CompositionCommonSchemaStableId': {'sourcePath': 'schemas/v1alpha1/composition/common.schema.json', 'schemaPointer': '/$defs/stableId', 'schemaId': None, 'requiredFields': []}, 'EvidencePlan': {'sourcePath': 'schemas/v1alpha1/composition/evidence-plan.schema.json', 'schemaPointer': '', 'schemaId': 'https://harness.planeon.ai/schemas/v1alpha1/composition/evidence-plan.schema.json', 'requiredFields': ['apiVersion', 'kind', 'metadata', 'spec']}, 'EvidenceRecord': {'sourcePath': 'schemas/v1alpha1/lifecycle/evidence-record.schema.json', 'schemaPointer': '', 'schemaId': 'https://harness.planeon.ai/schemas/v1alpha1/lifecycle/evidence-record.schema.json', 'requiredFields': ['apiVersion', 'kind', 'metadata', 'spec']}, 'ExecutionBudget': {'sourcePath': 'schemas/v1alpha1/composition/execution-budget.schema.json', 'schemaPointer': '', 'schemaId': 'https://harness.planeon.ai/schemas/v1alpha1/composition/execution-budget.schema.json', 'requiredFields': ['apiVersion', 'kind', 'metadata', 'spec']}, 'HarnessCloudEvent': {'sourcePath': 'schemas/v1alpha1/events/harness-cloud-event.schema.json', 'schemaPointer': '', 'schemaId': 'https://harness.planeon.ai/schemas/v1alpha1/events/harness-cloud-event.schema.json', 'requiredFields': ['data', 'datacontenttype', 'dataschema', 'id', 'organizationid', 'partitionkey', 'sequence', 'source', 'specversion', 'subject', 'time', 'type']}, 'HarnessInstallation': {'sourcePath': 'schemas/v1alpha1/lifecycle/harness-installation.schema.json', 'schemaPointer': '', 'schemaId': 'https://harness.planeon.ai/schemas/v1alpha1/lifecycle/harness-installation.schema.json', 'requiredFields': ['apiVersion', 'kind', 'metadata', 'spec']}, 'HarnessProfile': {'sourcePath': 'schemas/v1alpha1/composition/harness-profile.schema.json', 'schemaPointer': '', 'schemaId': 'https://harness.planeon.ai/schemas/v1alpha1/composition/harness-profile.schema.json', 'requiredFields': ['apiVersion', 'kind', 'metadata', 'spec']}, 'HarnessStatusProjection': {'sourcePath': 'schemas/v1alpha1/status/harness-status-projection.schema.json', 'schemaPointer': '', 'schemaId': 'https://harness.planeon.ai/schemas/v1alpha1/status/harness-status-projection.schema.json', 'requiredFields': ['apiVersion', 'binding', 'kind', 'metadata', 'spec']}, 'InstallPlan': {'sourcePath': 'schemas/v1alpha1/composition/install-plan.schema.json', 'schemaPointer': '', 'schemaId': 'https://harness.planeon.ai/schemas/v1alpha1/composition/install-plan.schema.json', 'requiredFields': ['apiVersion', 'kind', 'metadata', 'spec']}, 'LifecycleCommonSchemaActor': {'sourcePath': 'schemas/v1alpha1/lifecycle/common.schema.json', 'schemaPointer': '/$defs/actor', 'schemaId': None, 'requiredFields': ['id', 'type']}, 'LifecycleCommonSchemaApiVersion': {'sourcePath': 'schemas/v1alpha1/lifecycle/common.schema.json', 'schemaPointer': '/$defs/apiVersion', 'schemaId': None, 'requiredFields': []}, 'LifecycleCommonSchemaFailure': {'sourcePath': 'schemas/v1alpha1/lifecycle/common.schema.json', 'schemaPointer': '/$defs/failure', 'schemaId': None, 'requiredFields': ['evidenceRefs', 'reasonCode', 'retryable']}, 'LifecycleCommonSchemaImmutableBinding': {'sourcePath': 'schemas/v1alpha1/lifecycle/common.schema.json', 'schemaPointer': '/$defs/immutableBinding', 'schemaId': None, 'requiredFields': ['bundleDigest', 'organizationId', 'profileDigest', 'releaseDigest']}, 'LifecycleCommonSchemaMetadata': {'sourcePath': 'schemas/v1alpha1/lifecycle/common.schema.json', 'schemaPointer': '/$defs/metadata', 'schemaId': None, 'requiredFields': ['id', 'version']}, 'LifecycleCommonSchemaReasonCode': {'sourcePath': 'schemas/v1alpha1/lifecycle/common.schema.json', 'schemaPointer': '/$defs/reasonCode', 'schemaId': None, 'requiredFields': []}, 'LifecycleCommonSchemaResourceRef': {'sourcePath': 'schemas/v1alpha1/lifecycle/common.schema.json', 'schemaPointer': '/$defs/resourceRef', 'schemaId': None, 'requiredFields': ['digest', 'id', 'kind']}, 'LifecycleCommonSchemaSemver': {'sourcePath': 'schemas/v1alpha1/lifecycle/common.schema.json', 'schemaPointer': '/$defs/semver', 'schemaId': None, 'requiredFields': []}, 'LifecycleCommonSchemaSha256': {'sourcePath': 'schemas/v1alpha1/lifecycle/common.schema.json', 'schemaPointer': '/$defs/sha256', 'schemaId': None, 'requiredFields': []}, 'LifecycleCommonSchemaStableId': {'sourcePath': 'schemas/v1alpha1/lifecycle/common.schema.json', 'schemaPointer': '/$defs/stableId', 'schemaId': None, 'requiredFields': []}, 'LifecycleCommonSchemaTimestamp': {'sourcePath': 'schemas/v1alpha1/lifecycle/common.schema.json', 'schemaPointer': '/$defs/timestamp', 'schemaId': None, 'requiredFields': []}, 'Operation': {'sourcePath': 'schemas/v1alpha1/lifecycle/operation.schema.json', 'schemaPointer': '', 'schemaId': 'https://harness.planeon.ai/schemas/v1alpha1/lifecycle/operation.schema.json', 'requiredFields': ['apiVersion', 'kind', 'metadata', 'spec']}, 'OrganizationHarnessPortfolioPage': {'sourcePath': 'schemas/v1alpha1/status/organization-harness-portfolio-page.schema.json', 'schemaPointer': '', 'schemaId': 'https://harness.planeon.ai/schemas/v1alpha1/status/organization-harness-portfolio-page.schema.json', 'requiredFields': ['apiVersion', 'kind', 'metadata', 'spec']}, 'PlaneStatusProjection': {'sourcePath': 'schemas/v1alpha1/status/plane-status-projection.schema.json', 'schemaPointer': '', 'schemaId': 'https://harness.planeon.ai/schemas/v1alpha1/status/plane-status-projection.schema.json', 'requiredFields': ['apiVersion', 'binding', 'kind', 'metadata', 'spec']}, 'PolicyBundle': {'sourcePath': 'schemas/v1alpha1/lifecycle/policy-bundle.schema.json', 'schemaPointer': '', 'schemaId': 'https://harness.planeon.ai/schemas/v1alpha1/lifecycle/policy-bundle.schema.json', 'requiredFields': ['apiVersion', 'kind', 'metadata', 'spec']}, 'ProjectionFreshness': {'sourcePath': 'schemas/v1alpha1/status/projection-freshness.schema.json', 'schemaPointer': '', 'schemaId': 'https://harness.planeon.ai/schemas/v1alpha1/status/projection-freshness.schema.json', 'requiredFields': ['apiVersion', 'binding', 'kind', 'metadata', 'spec']}, 'StatusAxisProjection': {'sourcePath': 'schemas/v1alpha1/status/status-axis-projection.schema.json', 'schemaPointer': '', 'schemaId': 'https://harness.planeon.ai/schemas/v1alpha1/status/status-axis-projection.schema.json', 'requiredFields': ['apiVersion', 'binding', 'kind', 'metadata', 'spec']}, 'StatusCommonSchemaAggregateState': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/aggregateState', 'schemaId': None, 'requiredFields': []}, 'StatusCommonSchemaApiVersion': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/apiVersion', 'schemaId': None, 'requiredFields': []}, 'StatusCommonSchemaApplicability': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/applicability', 'schemaId': None, 'requiredFields': ['contractRef', 'reasonCode']}, 'StatusCommonSchemaEvidenceAxis': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/evidenceAxis', 'schemaId': None, 'requiredFields': []}, 'StatusCommonSchemaEvidenceState': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/evidenceState', 'schemaId': None, 'requiredFields': []}, 'StatusCommonSchemaFinding': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/finding', 'schemaId': None, 'requiredFields': ['affectedAxis', 'blocking', 'evidenceRefs', 'findingId', 'ownerRef', 'permittedActions', 'reasonCode', 'severity']}, 'StatusCommonSchemaFreshness': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/freshness', 'schemaId': None, 'requiredFields': ['freshUntil', 'projectedAt', 'sourceCursors', 'state']}, 'StatusCommonSchemaFreshnessState': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/freshnessState', 'schemaId': None, 'requiredFields': []}, 'StatusCommonSchemaHarnessSummary': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/harnessSummary', 'schemaId': None, 'requiredFields': ['aggregateState', 'blockerCount', 'freshnessState', 'harnessId', 'highestEvidenceState', 'installationState', 'planeId', 'reasonCode', 'selectionState']}, 'StatusCommonSchemaInstallationState': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/installationState', 'schemaId': None, 'requiredFields': []}, 'StatusCommonSchemaMetadata': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/metadata', 'schemaId': None, 'requiredFields': []}, 'StatusCommonSchemaNonWaivedEvidenceState': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/nonWaivedEvidenceState', 'schemaId': None, 'requiredFields': []}, 'StatusCommonSchemaPlaneSummary': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/planeSummary', 'schemaId': None, 'requiredFields': ['aggregateState', 'blockingDependencyCount', 'freshnessState', 'harnesses', 'notSelectedCount', 'planeId', 'selectedCount', 'worstInstallationState']}, 'StatusCommonSchemaProjectionBinding': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/projectionBinding', 'schemaId': None, 'requiredFields': ['bundleDigest', 'freshUntil', 'observedGeneration', 'organizationId', 'profileDigest', 'projectedAt', 'projectionSchemaVersion', 'releaseDigest', 'sourceCursors']}, 'StatusCommonSchemaReasonCode': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/reasonCode', 'schemaId': None, 'requiredFields': []}, 'StatusCommonSchemaResourceRef': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/resourceRef', 'schemaId': None, 'requiredFields': []}, 'StatusCommonSchemaSelectionState': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/selectionState', 'schemaId': None, 'requiredFields': []}, 'StatusCommonSchemaSemver': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/semver', 'schemaId': None, 'requiredFields': []}, 'StatusCommonSchemaSha256': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/sha256', 'schemaId': None, 'requiredFields': []}, 'StatusCommonSchemaSourceCursor': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/sourceCursor', 'schemaId': None, 'requiredFields': ['cursor', 'observedAt', 'sourceId', 'state']}, 'StatusCommonSchemaStableId': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/stableId', 'schemaId': None, 'requiredFields': []}, 'StatusCommonSchemaStateCount': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/stateCount', 'schemaId': None, 'requiredFields': ['count', 'state']}, 'StatusCommonSchemaStatusAxis': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/statusAxis', 'schemaId': None, 'requiredFields': ['applicability', 'axis', 'evidenceRefs', 'observedAt', 'required', 'state', 'underlyingState', 'waiver']}, 'StatusCommonSchemaTimestamp': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/timestamp', 'schemaId': None, 'requiredFields': []}, 'StatusCommonSchemaWaiver': {'sourcePath': 'schemas/v1alpha1/status/common.schema.json', 'schemaPointer': '/$defs/waiver', 'schemaId': None, 'requiredFields': ['approvedBy', 'basisCode', 'expiresAt', 'waiverDigest', 'waiverId']}, 'StatusFindingSummary': {'sourcePath': 'schemas/v1alpha1/status/status-finding-summary.schema.json', 'schemaPointer': '', 'schemaId': 'https://harness.planeon.ai/schemas/v1alpha1/status/status-finding-summary.schema.json', 'requiredFields': ['apiVersion', 'binding', 'kind', 'metadata', 'spec']}, 'TenantDemand': {'sourcePath': 'schemas/v1alpha1/composition/tenant-demand.schema.json', 'schemaPointer': '', 'schemaId': 'https://harness.planeon.ai/schemas/v1alpha1/composition/tenant-demand.schema.json', 'requiredFields': ['apiVersion', 'kind', 'metadata', 'spec']}, 'TenantHarnessOverview': {'sourcePath': 'schemas/v1alpha1/status/tenant-harness-overview.schema.json', 'schemaPointer': '', 'schemaId': 'https://harness.planeon.ai/schemas/v1alpha1/status/tenant-harness-overview.schema.json', 'requiredFields': ['apiVersion', 'binding', 'kind', 'metadata', 'spec']}}
