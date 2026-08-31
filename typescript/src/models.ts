// Generated contract models. Do not edit by hand.
export type JsonScalar = null | boolean | number | string;
export type JsonValue = JsonScalar | Array<JsonValue> | JsonObject;
export interface JsonObject { [key: string]: JsonValue; }
export const CONTRACT_RELEASE_DIGEST = "sha256:76c6098ce16da7e5c45d7955feb65f4972715c803e4f989443def0edbca38105" as const;

export interface ApprovalDecision {
  decision: "APPROVE" | "REJECT";
  reasonCode: string;
}

export interface ApprovalRequest {
  apiVersion: JsonValue;
  kind: "ApprovalRequest";
  metadata: JsonValue;
  spec: JsonObject;
}

export interface BillOfMaterials {
  apiVersion: JsonValue;
  kind: "BillOfMaterials";
  metadata: JsonValue;
  spec: JsonObject;
}

export interface BundleRelease {
  apiVersion: JsonValue;
  kind: "BundleRelease";
  metadata: JsonValue;
  spec: JsonObject;
}

export interface CompileRequest {
  demand: JsonObject;
  metadata: JsonObject;
  questionnaireAnswerSet: JsonValue;
  readinessAssessment: JsonValue;
  schemaVersion: "harness.planeon.ai/compile-request/v1alpha1";
}

export interface CompiledProfileDocument {
  executionBudget: JsonValue;
  profile: JsonValue;
  schemaVersion: "harness.planeon.ai/compiled-profile-document/v1alpha1";
  tenantDemand: JsonValue;
}

export interface CompositionCommonSchemaApiVersion {
}

export interface CompositionCommonSchemaAssuranceSubjects {
  capabilityIds: Array<JsonValue>;
  harnessIds: Array<JsonValue>;
}

export interface CompositionCommonSchemaEnvironment {
  architecture: "amd64" | "arm64" | "platform-supplied";
  attestationDigest: JsonValue;
  capabilities: Array<JsonValue>;
  deploymentMode: "operator-hosted-saas" | "tenant-public-cloud" | "self-managed" | "air-gapped";
  kubernetesDistribution: "upstream" | "k3s" | "openshift" | "none" | "platform-supplied";
  operatingSystem: "linux" | "macos" | "platform-supplied";
  signatureStatus: "VERIFIED";
  tenantId: JsonValue;
}

export interface CompositionCommonSchemaExecutionBudgetSpec {
  maxConcurrentTasks: number;
  maxModelTokens: number;
  maxRetries: number;
  maxTaskSeconds: number;
  maxToolCalls: number;
}

export interface CompositionCommonSchemaInstallUnit {
  artifactName: JsonValue;
  digest: null;
  digestStatus: "MISSING_PLANNED";
  id: JsonValue;
  type: "OCI_IMAGE" | "OCI_ARTIFACT" | "HELM_CHART" | "PYTHON_WHEEL" | "NPM_TARBALL" | "LOCAL_BINARY" | "KUBERNETES_RUNTIME_CLASS" | "TENANT_SUPPLIED_PLATFORM";
}

export interface CompositionCommonSchemaMetadata {
  id: JsonValue;
  version: JsonValue;
}

export interface CompositionCommonSchemaProviderSelection {
  groupId: JsonValue;
  providerId: JsonValue;
  selectorCapability: JsonValue;
}

export interface CompositionCommonSchemaSelectorProposal {
  disposition: "PROPOSED_SELECTOR_ONLY";
  groupId: JsonValue;
  selectorCapabilities: Array<JsonValue>;
}

export interface CompositionCommonSchemaSemver {
}

export interface CompositionCommonSchemaSha256 {
}

export interface CompositionCommonSchemaStableId {
}

export interface EvidencePlan {
  apiVersion: JsonValue;
  kind: "EvidencePlan";
  metadata: JsonValue;
  spec: JsonObject;
}

export interface EvidenceRecord {
  apiVersion: JsonValue;
  kind: "EvidenceRecord";
  metadata: JsonValue;
  spec: JsonObject;
}

export interface ExecutionBudget {
  apiVersion: JsonValue;
  kind: "ExecutionBudget";
  metadata: JsonValue;
  spec: JsonObject;
}

export interface HarnessCloudEvent {
  data: JsonObject;
  datacontenttype: "application/json";
  dataschema: "https://harness.planeon.ai/schemas/v1alpha1/events/harness-cloud-event.schema.json";
  id: string;
  organizationid: JsonValue;
  partitionkey: JsonValue;
  sequence: number;
  source: string;
  specversion: "1.0";
  subject: JsonValue;
  time: JsonValue;
  type: "harness.approval.state.changed.v1" | "harness.bundle-release.state.changed.v1" | "harness.evidence.state.changed.v1" | "harness.installation.state.changed.v1" | "harness.operation.state.changed.v1" | "harness.policy-bundle.state.changed.v1" | "harness.status.projection.updated.v1";
}

export interface HarnessInstallation {
  apiVersion: JsonValue;
  kind: "HarnessInstallation";
  metadata: JsonValue;
  spec: JsonObject;
}

export interface HarnessProfile {
  apiVersion: JsonValue;
  kind: "HarnessProfile";
  metadata: JsonValue;
  spec: JsonObject;
}

export interface HarnessStatusProjection {
  apiVersion: JsonValue;
  binding: JsonValue;
  kind: "HarnessStatusProjection";
  metadata: JsonValue;
  spec: JsonObject;
}

export interface InstallPlan {
  apiVersion: JsonValue;
  kind: "InstallPlan";
  metadata: JsonValue;
  spec: JsonObject;
}

export interface LifecycleCommonSchemaActor {
  id: JsonValue;
  type: "HUMAN" | "WORKLOAD" | "SYSTEM" | "TENANT";
}

export interface LifecycleCommonSchemaApiVersion {
}

export interface LifecycleCommonSchemaFailure {
  evidenceRefs: Array<JsonValue>;
  reasonCode: JsonValue;
  retryable: boolean;
}

export interface LifecycleCommonSchemaImmutableBinding {
  bundleDigest: JsonValue;
  organizationId: JsonValue;
  profileDigest: JsonValue;
  releaseDigest: JsonValue;
}

export interface LifecycleCommonSchemaMetadata {
  id: JsonValue;
  version: JsonValue;
}

export interface LifecycleCommonSchemaReasonCode {
}

export interface LifecycleCommonSchemaResourceRef {
  digest: JsonValue;
  id: JsonValue;
  kind: JsonValue;
}

export interface LifecycleCommonSchemaSemver {
}

export interface LifecycleCommonSchemaSha256 {
}

export interface LifecycleCommonSchemaStableId {
}

export interface LifecycleCommonSchemaTimestamp {
}

export interface Operation {
  apiVersion: JsonValue;
  kind: "Operation";
  metadata: JsonValue;
  spec: JsonObject;
}

export interface OrganizationHarnessPortfolioPage {
  apiVersion: JsonValue;
  kind: "OrganizationHarnessPortfolioPage";
  metadata: JsonValue;
  spec: JsonObject;
}

export interface PlaneStatusProjection {
  apiVersion: JsonValue;
  binding: JsonValue;
  kind: "PlaneStatusProjection";
  metadata: JsonValue;
  spec: JsonObject;
}

export interface PolicyBundle {
  apiVersion: JsonValue;
  kind: "PolicyBundle";
  metadata: JsonValue;
  spec: JsonObject;
}

export interface ProjectionFreshness {
  apiVersion: JsonValue;
  binding: JsonValue;
  kind: "ProjectionFreshness";
  metadata: JsonValue;
  spec: JsonValue;
}

export interface StatusAxisProjection {
  apiVersion: JsonValue;
  binding: JsonValue;
  kind: "StatusAxisProjection";
  metadata: JsonValue;
  spec: JsonValue;
}

export interface StatusCommonSchemaAggregateState {
}

export interface StatusCommonSchemaApiVersion {
}

export interface StatusCommonSchemaApplicability {
  contractRef: JsonValue;
  reasonCode: JsonValue;
}

export interface StatusCommonSchemaEvidenceAxis {
}

export interface StatusCommonSchemaEvidenceState {
}

export interface StatusCommonSchemaFinding {
  affectedAxis: JsonValue;
  blocking: boolean;
  evidenceRefs: Array<JsonValue>;
  findingId: JsonValue;
  ownerRef: JsonValue;
  permittedActions: Array<"REQUEST_EVIDENCE" | "REFRESH_PROJECTION" | "REVIEW_WAIVER" | "RETRY_OPERATION" | "ROLLBACK" | "RESOLVE_DEPENDENCY" | "CONTACT_OWNER" | "NONE">;
  reasonCode: JsonValue;
  severity: "INFO" | "WARN" | "ERROR" | "CRITICAL";
}

export interface StatusCommonSchemaFreshness {
  freshUntil: JsonValue;
  projectedAt: JsonValue;
  sourceCursors: Array<JsonValue>;
  state: JsonValue;
}

export interface StatusCommonSchemaFreshnessState {
}

export interface StatusCommonSchemaHarnessSummary {
  aggregateState: JsonValue;
  blockerCount: number;
  freshnessState: JsonValue;
  harnessId: JsonValue;
  highestEvidenceState: JsonValue;
  installationState: JsonValue;
  planeId: "runtime" | "knowledge" | "execution" | "trust";
  reasonCode: JsonValue;
  selectionState: JsonValue;
}

export interface StatusCommonSchemaInstallationState {
}

export interface StatusCommonSchemaMetadata {
}

export interface StatusCommonSchemaNonWaivedEvidenceState {
}

export interface StatusCommonSchemaPlaneSummary {
  aggregateState: JsonValue;
  blockingDependencyCount: number;
  freshnessState: JsonValue;
  harnesses: Array<JsonValue>;
  notSelectedCount: number;
  planeId: "runtime" | "knowledge" | "execution" | "trust";
  selectedCount: number;
  worstInstallationState: JsonValue;
}

export interface StatusCommonSchemaProjectionBinding {
  bundleDigest: JsonValue;
  freshUntil: JsonValue;
  observedGeneration: number;
  organizationId: JsonValue;
  profileDigest: JsonValue;
  projectedAt: JsonValue;
  projectionSchemaVersion: "harness.planeon.ai/status-projection/v1alpha1";
  releaseDigest: JsonValue;
  sourceCursors: Array<JsonValue>;
}

export interface StatusCommonSchemaReasonCode {
}

export interface StatusCommonSchemaResourceRef {
}

export interface StatusCommonSchemaSelectionState {
}

export interface StatusCommonSchemaSemver {
}

export interface StatusCommonSchemaSha256 {
}

export interface StatusCommonSchemaSourceCursor {
  cursor: string;
  observedAt: JsonValue;
  sourceId: JsonValue;
  state: "CURRENT" | "SOURCE_UNAVAILABLE";
}

export interface StatusCommonSchemaStableId {
}

export interface StatusCommonSchemaStateCount {
  count: number;
  state: string;
}

export interface StatusCommonSchemaStatusAxis {
  applicability: JsonValue;
  axis: JsonValue;
  evidenceRefs: Array<JsonValue>;
  observedAt: JsonValue;
  required: boolean;
  state: JsonValue;
  underlyingState: JsonValue;
  waiver: JsonValue;
}

export interface StatusCommonSchemaTimestamp {
}

export interface StatusCommonSchemaWaiver {
  approvedBy: JsonValue;
  basisCode: JsonValue;
  expiresAt: JsonValue;
  waiverDigest: JsonValue;
  waiverId: JsonValue;
}

export interface StatusFindingSummary {
  apiVersion: JsonValue;
  binding: JsonValue;
  kind: "StatusFindingSummary";
  metadata: JsonValue;
  spec: JsonValue;
}

export interface TenantDemand {
  apiVersion: JsonValue;
  kind: "TenantDemand";
  metadata: JsonValue;
  spec: JsonObject;
}

export interface TenantHarnessOverview {
  apiVersion: JsonValue;
  binding: JsonValue;
  kind: "TenantHarnessOverview";
  metadata: JsonValue;
  spec: JsonObject;
}

export const MODEL_CONTRACTS = {"ApprovalDecision":{"requiredFields":["decision","reasonCode"],"schemaId":null,"schemaPointer":"/components/schemas/ApprovalDecision","sourcePath":"openapi/control-plane.openapi.json"},"ApprovalRequest":{"requiredFields":["apiVersion","kind","metadata","spec"],"schemaId":"https://harness.planeon.ai/schemas/v1alpha1/lifecycle/approval-request.schema.json","schemaPointer":"","sourcePath":"schemas/v1alpha1/lifecycle/approval-request.schema.json"},"BillOfMaterials":{"requiredFields":["apiVersion","kind","metadata","spec"],"schemaId":"https://harness.planeon.ai/schemas/v1alpha1/composition/bill-of-materials.schema.json","schemaPointer":"","sourcePath":"schemas/v1alpha1/composition/bill-of-materials.schema.json"},"BundleRelease":{"requiredFields":["apiVersion","kind","metadata","spec"],"schemaId":"https://harness.planeon.ai/schemas/v1alpha1/lifecycle/bundle-release.schema.json","schemaPointer":"","sourcePath":"schemas/v1alpha1/lifecycle/bundle-release.schema.json"},"CompileRequest":{"requiredFields":["demand","metadata","questionnaireAnswerSet","readinessAssessment","schemaVersion"],"schemaId":"https://harness.planeon.ai/schemas/v1alpha1/composition/compile-request.schema.json","schemaPointer":"","sourcePath":"schemas/v1alpha1/composition/compile-request.schema.json"},"CompiledProfileDocument":{"requiredFields":["executionBudget","profile","schemaVersion","tenantDemand"],"schemaId":"https://harness.planeon.ai/schemas/v1alpha1/composition/compiled-profile-document.schema.json","schemaPointer":"","sourcePath":"schemas/v1alpha1/composition/compiled-profile-document.schema.json"},"CompositionCommonSchemaApiVersion":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/apiVersion","sourcePath":"schemas/v1alpha1/composition/common.schema.json"},"CompositionCommonSchemaAssuranceSubjects":{"requiredFields":["capabilityIds","harnessIds"],"schemaId":null,"schemaPointer":"/$defs/assuranceSubjects","sourcePath":"schemas/v1alpha1/composition/common.schema.json"},"CompositionCommonSchemaEnvironment":{"requiredFields":["architecture","attestationDigest","capabilities","deploymentMode","kubernetesDistribution","operatingSystem","signatureStatus","tenantId"],"schemaId":null,"schemaPointer":"/$defs/environment","sourcePath":"schemas/v1alpha1/composition/common.schema.json"},"CompositionCommonSchemaExecutionBudgetSpec":{"requiredFields":["maxConcurrentTasks","maxModelTokens","maxRetries","maxTaskSeconds","maxToolCalls"],"schemaId":null,"schemaPointer":"/$defs/executionBudgetSpec","sourcePath":"schemas/v1alpha1/composition/common.schema.json"},"CompositionCommonSchemaInstallUnit":{"requiredFields":["artifactName","digest","digestStatus","id","type"],"schemaId":null,"schemaPointer":"/$defs/installUnit","sourcePath":"schemas/v1alpha1/composition/common.schema.json"},"CompositionCommonSchemaMetadata":{"requiredFields":["id","version"],"schemaId":null,"schemaPointer":"/$defs/metadata","sourcePath":"schemas/v1alpha1/composition/common.schema.json"},"CompositionCommonSchemaProviderSelection":{"requiredFields":["groupId","providerId","selectorCapability"],"schemaId":null,"schemaPointer":"/$defs/providerSelection","sourcePath":"schemas/v1alpha1/composition/common.schema.json"},"CompositionCommonSchemaSelectorProposal":{"requiredFields":["disposition","groupId","selectorCapabilities"],"schemaId":null,"schemaPointer":"/$defs/selectorProposal","sourcePath":"schemas/v1alpha1/composition/common.schema.json"},"CompositionCommonSchemaSemver":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/semver","sourcePath":"schemas/v1alpha1/composition/common.schema.json"},"CompositionCommonSchemaSha256":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/sha256","sourcePath":"schemas/v1alpha1/composition/common.schema.json"},"CompositionCommonSchemaStableId":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/stableId","sourcePath":"schemas/v1alpha1/composition/common.schema.json"},"EvidencePlan":{"requiredFields":["apiVersion","kind","metadata","spec"],"schemaId":"https://harness.planeon.ai/schemas/v1alpha1/composition/evidence-plan.schema.json","schemaPointer":"","sourcePath":"schemas/v1alpha1/composition/evidence-plan.schema.json"},"EvidenceRecord":{"requiredFields":["apiVersion","kind","metadata","spec"],"schemaId":"https://harness.planeon.ai/schemas/v1alpha1/lifecycle/evidence-record.schema.json","schemaPointer":"","sourcePath":"schemas/v1alpha1/lifecycle/evidence-record.schema.json"},"ExecutionBudget":{"requiredFields":["apiVersion","kind","metadata","spec"],"schemaId":"https://harness.planeon.ai/schemas/v1alpha1/composition/execution-budget.schema.json","schemaPointer":"","sourcePath":"schemas/v1alpha1/composition/execution-budget.schema.json"},"HarnessCloudEvent":{"requiredFields":["data","datacontenttype","dataschema","id","organizationid","partitionkey","sequence","source","specversion","subject","time","type"],"schemaId":"https://harness.planeon.ai/schemas/v1alpha1/events/harness-cloud-event.schema.json","schemaPointer":"","sourcePath":"schemas/v1alpha1/events/harness-cloud-event.schema.json"},"HarnessInstallation":{"requiredFields":["apiVersion","kind","metadata","spec"],"schemaId":"https://harness.planeon.ai/schemas/v1alpha1/lifecycle/harness-installation.schema.json","schemaPointer":"","sourcePath":"schemas/v1alpha1/lifecycle/harness-installation.schema.json"},"HarnessProfile":{"requiredFields":["apiVersion","kind","metadata","spec"],"schemaId":"https://harness.planeon.ai/schemas/v1alpha1/composition/harness-profile.schema.json","schemaPointer":"","sourcePath":"schemas/v1alpha1/composition/harness-profile.schema.json"},"HarnessStatusProjection":{"requiredFields":["apiVersion","binding","kind","metadata","spec"],"schemaId":"https://harness.planeon.ai/schemas/v1alpha1/status/harness-status-projection.schema.json","schemaPointer":"","sourcePath":"schemas/v1alpha1/status/harness-status-projection.schema.json"},"InstallPlan":{"requiredFields":["apiVersion","kind","metadata","spec"],"schemaId":"https://harness.planeon.ai/schemas/v1alpha1/composition/install-plan.schema.json","schemaPointer":"","sourcePath":"schemas/v1alpha1/composition/install-plan.schema.json"},"LifecycleCommonSchemaActor":{"requiredFields":["id","type"],"schemaId":null,"schemaPointer":"/$defs/actor","sourcePath":"schemas/v1alpha1/lifecycle/common.schema.json"},"LifecycleCommonSchemaApiVersion":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/apiVersion","sourcePath":"schemas/v1alpha1/lifecycle/common.schema.json"},"LifecycleCommonSchemaFailure":{"requiredFields":["evidenceRefs","reasonCode","retryable"],"schemaId":null,"schemaPointer":"/$defs/failure","sourcePath":"schemas/v1alpha1/lifecycle/common.schema.json"},"LifecycleCommonSchemaImmutableBinding":{"requiredFields":["bundleDigest","organizationId","profileDigest","releaseDigest"],"schemaId":null,"schemaPointer":"/$defs/immutableBinding","sourcePath":"schemas/v1alpha1/lifecycle/common.schema.json"},"LifecycleCommonSchemaMetadata":{"requiredFields":["id","version"],"schemaId":null,"schemaPointer":"/$defs/metadata","sourcePath":"schemas/v1alpha1/lifecycle/common.schema.json"},"LifecycleCommonSchemaReasonCode":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/reasonCode","sourcePath":"schemas/v1alpha1/lifecycle/common.schema.json"},"LifecycleCommonSchemaResourceRef":{"requiredFields":["digest","id","kind"],"schemaId":null,"schemaPointer":"/$defs/resourceRef","sourcePath":"schemas/v1alpha1/lifecycle/common.schema.json"},"LifecycleCommonSchemaSemver":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/semver","sourcePath":"schemas/v1alpha1/lifecycle/common.schema.json"},"LifecycleCommonSchemaSha256":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/sha256","sourcePath":"schemas/v1alpha1/lifecycle/common.schema.json"},"LifecycleCommonSchemaStableId":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/stableId","sourcePath":"schemas/v1alpha1/lifecycle/common.schema.json"},"LifecycleCommonSchemaTimestamp":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/timestamp","sourcePath":"schemas/v1alpha1/lifecycle/common.schema.json"},"Operation":{"requiredFields":["apiVersion","kind","metadata","spec"],"schemaId":"https://harness.planeon.ai/schemas/v1alpha1/lifecycle/operation.schema.json","schemaPointer":"","sourcePath":"schemas/v1alpha1/lifecycle/operation.schema.json"},"OrganizationHarnessPortfolioPage":{"requiredFields":["apiVersion","kind","metadata","spec"],"schemaId":"https://harness.planeon.ai/schemas/v1alpha1/status/organization-harness-portfolio-page.schema.json","schemaPointer":"","sourcePath":"schemas/v1alpha1/status/organization-harness-portfolio-page.schema.json"},"PlaneStatusProjection":{"requiredFields":["apiVersion","binding","kind","metadata","spec"],"schemaId":"https://harness.planeon.ai/schemas/v1alpha1/status/plane-status-projection.schema.json","schemaPointer":"","sourcePath":"schemas/v1alpha1/status/plane-status-projection.schema.json"},"PolicyBundle":{"requiredFields":["apiVersion","kind","metadata","spec"],"schemaId":"https://harness.planeon.ai/schemas/v1alpha1/lifecycle/policy-bundle.schema.json","schemaPointer":"","sourcePath":"schemas/v1alpha1/lifecycle/policy-bundle.schema.json"},"ProjectionFreshness":{"requiredFields":["apiVersion","binding","kind","metadata","spec"],"schemaId":"https://harness.planeon.ai/schemas/v1alpha1/status/projection-freshness.schema.json","schemaPointer":"","sourcePath":"schemas/v1alpha1/status/projection-freshness.schema.json"},"StatusAxisProjection":{"requiredFields":["apiVersion","binding","kind","metadata","spec"],"schemaId":"https://harness.planeon.ai/schemas/v1alpha1/status/status-axis-projection.schema.json","schemaPointer":"","sourcePath":"schemas/v1alpha1/status/status-axis-projection.schema.json"},"StatusCommonSchemaAggregateState":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/aggregateState","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaApiVersion":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/apiVersion","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaApplicability":{"requiredFields":["contractRef","reasonCode"],"schemaId":null,"schemaPointer":"/$defs/applicability","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaEvidenceAxis":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/evidenceAxis","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaEvidenceState":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/evidenceState","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaFinding":{"requiredFields":["affectedAxis","blocking","evidenceRefs","findingId","ownerRef","permittedActions","reasonCode","severity"],"schemaId":null,"schemaPointer":"/$defs/finding","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaFreshness":{"requiredFields":["freshUntil","projectedAt","sourceCursors","state"],"schemaId":null,"schemaPointer":"/$defs/freshness","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaFreshnessState":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/freshnessState","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaHarnessSummary":{"requiredFields":["aggregateState","blockerCount","freshnessState","harnessId","highestEvidenceState","installationState","planeId","reasonCode","selectionState"],"schemaId":null,"schemaPointer":"/$defs/harnessSummary","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaInstallationState":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/installationState","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaMetadata":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/metadata","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaNonWaivedEvidenceState":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/nonWaivedEvidenceState","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaPlaneSummary":{"requiredFields":["aggregateState","blockingDependencyCount","freshnessState","harnesses","notSelectedCount","planeId","selectedCount","worstInstallationState"],"schemaId":null,"schemaPointer":"/$defs/planeSummary","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaProjectionBinding":{"requiredFields":["bundleDigest","freshUntil","observedGeneration","organizationId","profileDigest","projectedAt","projectionSchemaVersion","releaseDigest","sourceCursors"],"schemaId":null,"schemaPointer":"/$defs/projectionBinding","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaReasonCode":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/reasonCode","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaResourceRef":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/resourceRef","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaSelectionState":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/selectionState","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaSemver":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/semver","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaSha256":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/sha256","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaSourceCursor":{"requiredFields":["cursor","observedAt","sourceId","state"],"schemaId":null,"schemaPointer":"/$defs/sourceCursor","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaStableId":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/stableId","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaStateCount":{"requiredFields":["count","state"],"schemaId":null,"schemaPointer":"/$defs/stateCount","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaStatusAxis":{"requiredFields":["applicability","axis","evidenceRefs","observedAt","required","state","underlyingState","waiver"],"schemaId":null,"schemaPointer":"/$defs/statusAxis","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaTimestamp":{"requiredFields":[],"schemaId":null,"schemaPointer":"/$defs/timestamp","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusCommonSchemaWaiver":{"requiredFields":["approvedBy","basisCode","expiresAt","waiverDigest","waiverId"],"schemaId":null,"schemaPointer":"/$defs/waiver","sourcePath":"schemas/v1alpha1/status/common.schema.json"},"StatusFindingSummary":{"requiredFields":["apiVersion","binding","kind","metadata","spec"],"schemaId":"https://harness.planeon.ai/schemas/v1alpha1/status/status-finding-summary.schema.json","schemaPointer":"","sourcePath":"schemas/v1alpha1/status/status-finding-summary.schema.json"},"TenantDemand":{"requiredFields":["apiVersion","kind","metadata","spec"],"schemaId":"https://harness.planeon.ai/schemas/v1alpha1/composition/tenant-demand.schema.json","schemaPointer":"","sourcePath":"schemas/v1alpha1/composition/tenant-demand.schema.json"},"TenantHarnessOverview":{"requiredFields":["apiVersion","binding","kind","metadata","spec"],"schemaId":"https://harness.planeon.ai/schemas/v1alpha1/status/tenant-harness-overview.schema.json","schemaPointer":"","sourcePath":"schemas/v1alpha1/status/tenant-harness-overview.schema.json"}} as const;
