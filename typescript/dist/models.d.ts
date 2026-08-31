// Generated model declarations. Do not edit by hand.
export type JsonScalar = null | boolean | number | string;
export type JsonValue = JsonScalar | Array<JsonValue> | JsonObject;
export interface JsonObject { [key: string]: JsonValue; }
export declare const CONTRACT_RELEASE_DIGEST: "sha256:76c6098ce16da7e5c45d7955feb65f4972715c803e4f989443def0edbca38105";

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

export declare const MODEL_CONTRACTS: Readonly<Record<string, {
  readonly sourcePath: string;
  readonly schemaPointer: string;
  readonly schemaId: string | null;
  readonly requiredFields: ReadonlyArray<string>;
}>>;
