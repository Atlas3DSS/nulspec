import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

export const NOMINATE_URL = "/#nominate";
export const KOFI_URL = "https://ko-fi.com/nulspec";
export const GITHUB_URL = "https://github.com/Atlas3DSS/nulspec";

export type ArmState = "QUEUED" | "RUNNING" | "DONE" | "FAILED" | "ABORTED";
export type Provenance = "EXACT" | "COMPAT";
export type Verdict = "MATCH" | "DIVERGES" | "INCONCLUSIVE";
export type Classification =
  | "REPRODUCED"
  | "PARTIALLY_REPRODUCED"
  | "NOT_REPRODUCED"
  | "INCONCLUSIVE";
export type StudyState =
  | "SPEC-FROZEN"
  | "RUNNING"
  | "RUNS-COMPLETE"
  | "ANALYSIS-OPEN"
  | "REPORTED";

export interface ArmMetrics {
  published_reward_delta: number;
  release_reward_delta: number;
  release_prompt_bootstrap_95_ci: [number, number];
  published_delta_inside_release_interval: boolean;
  independent_paired_reward_delta: number;
  independent_paired_bootstrap_95_ci: [number, number];
  independent_paired_sign_flip_pvalue_holm_15: number;
  directional_assessment:
    | "agrees"
    | "disagrees"
    | "inconclusive_interval_includes_zero";
}

export interface PublicationArm {
  ordinal: number;
  arm_id: string;
  track: string;
  model: string;
  dataset: string;
  seed: number;
  execution:
    | "completed"
    | "completed_with_recovery"
    | "failed"
    | "aborted"
    | "inconclusive_terminal";
  claim_ready: boolean;
  recovery_used: boolean;
  gpu: string;
  host: string;
  provenance: Provenance;
  verdict: Verdict;
  metrics: ArmMetrics;
}

export interface PublicationArtifact {
  role: "result_summary" | "full_report" | "machine_analysis" | string;
  path: string;
  public_path: string;
  media_type: string;
  sha256: string;
}

export interface PublicationTrack {
  id: string;
  label?: string;
  registered_arms: number;
  terminal_arms: number;
  claim_ready_arms: number;
  execution_counts?: Record<string, number>;
  direction_counts?: Record<string, number>;
  published_deltas_inside_interval?: number;
}

export interface ExtensionOption {
  id: string;
  label: string;
  role: string;
  priority: number;
  summary: string;
}

export interface ExtensionCallToAction {
  requested: true;
  implementation_owner: "website_team";
  button_label: string;
  prompt: string;
  selection_mode: "single_choice";
  options: ExtensionOption[];
}

export interface EvidenceNavigation {
  requested: true;
  implementation_owner: "website_team";
  route_contract: {
    arm_detail: string;
    comparison_fragment: "#comparison";
    execution_fragment: "#execution";
    provenance_fragment: "#provenance";
    evidence_fragment: "#evidence";
    future_attempts_fragment: "#attempts";
  };
  matrix_interaction: {
    explicit_link_label: string;
    accessibility_requirement: string;
  };
  arm_page_mvp: {
    status: "implementable_from_current_publication_bundle";
    comparison_rules: string[];
  };
  phase_two_evidence_index: {
    status: "not_yet_public";
    proposed_artifact: string;
    frontend_behavior_until_available: string;
  };
}

export interface PublicationBundle {
  schema_version: 1;
  publication_status: "ready";
  generated_at_utc: string;
  study: {
    id: string;
    slug: string;
    title: string;
    claim_under_test: string;
    paper: {
      title: string;
      arxiv_id: string;
      url: string;
    };
  };
  source: {
    repository: string;
    visibility?: "public" | "private";
    evidence_revision: string;
  };
  protocol: {
    version: string;
    base_version?: string;
    tag?: string;
    freeze_revision: string;
    matrix_sha256: string;
    config_sha256: string;
  };
  completion: {
    registered_arms: number;
    terminal_arms: number;
    claim_ready_arms: number;
    tracks: PublicationTrack[];
    gates: Record<string, boolean>;
  };
  verdict: {
    classification: Classification;
    headline: string;
    summary: string;
    key_findings: string[];
    limitations: string[];
  };
  artifacts: PublicationArtifact[];
  arms: PublicationArm[];
  deviations: Array<{
    id: string;
    scope: string;
    description: string;
    control: string;
  }>;
  evidence_navigation: EvidenceNavigation;
  extension_call_to_action?: ExtensionCallToAction;
  frozen_primary_result?: {
    registered_arms: number;
    claim_ready_arms: number;
    may_be_rewritten_by_extension: false;
  };
}

export interface AccuracyAggregate {
  mean: number;
  n_training_seeds: number;
  sample_sd: number;
  descriptive_t95_interval: [number, number];
  per_seed: number[];
  estimator: "final_sample_weighted_full_validation_accuracy";
  unit: "percent_accuracy";
}

export interface AccuracyMetricSummary {
  model_key: string;
  observed: AccuracyAggregate;
  reported_accuracy?: number;
  reported_accuracy_inside_descriptive_t95?: boolean;
}

export interface AccuracyPointDifference {
  mean: number;
  n: number;
  sample_sd: number;
  t95_interval: [number, number];
  values: number[];
}

export interface McNemarExactResult {
  a_correct_b_correct: number;
  a_correct_b_wrong: number;
  a_wrong_b_correct: number;
  a_wrong_b_wrong: number;
  accuracy_a: number;
  accuracy_b: number;
  log10_p_value: number;
  method: string;
  n: number;
  p_value: number;
  seed: number;
  statistic: number;
}

export interface AccuracyComparison {
  accuracy_point_difference: AccuracyPointDifference;
  per_seed_mcnemar_exact: McNemarExactResult[];
}

export interface AccuracyRunComparison {
  accuracy_point_difference: number;
  mcnemar_exact: McNemarExactResult;
  unit: "percentage_points";
}

export interface AccuracyRunModel {
  accuracy_sample_weighted: number;
  best_valid_accuracy_unweighted_batch_mean?: number;
  cross_entropy_sample_weighted: number;
  elapsed_seconds?: number;
  final_valid_accuracy_unweighted_batch_mean?: number;
  model_key: string;
  parameter_count?: number;
}

export interface AccuracyRun {
  run_id: string;
  seed: number;
  route: string;
  gpu: string;
  environment: {
    cuda_runtime: string;
    cudnn: number;
    gpu: {
      compute_capability: string;
      name: string;
      total_memory_bytes: number;
    };
    numpy: string;
    platform: string;
    python: string;
    torch: string;
  };
  integrity: {
    complete_sha256: string;
    config_sha256: string;
    n_validation_targets: number;
    predictions_sha256: string;
    split_indices_sha256: string;
    stage_checkpoint_sha256s: Record<string, string>;
    stage_count: number;
    status: "passed";
    validation_indices_sha256: string;
  };
  models: Record<string, AccuracyRunModel>;
  metrics: Record<string, number>;
  comparisons: Record<string, AccuracyRunComparison>;
}

export interface AccuracyExtensionVote {
  button_label: "Vote to extend this paper";
  question: string;
  choices: Array<{
    id: string;
    label: string;
    role: string;
  }>;
  effect: string;
}

export interface FinalPeerReviewState {
  protocol: "nulspec-fable-one-shot-final-gate-v1";
  protocol_document: string;
  reviewer: "Fable";
  single_invocation: true;
  resubmission_allowed: false;
  status:
    | "approved"
    | "approved_after_three_action_closure"
    | "approved_after_human_disposition";
  publication_authorized: true;
  author_email_eligible_for_human_approval: true;
  author_email_dispatch_authorized: boolean;
  author_email_human_approval_required: true;
  author_email_approval_status:
    | "pending_final_human_approval"
    | "approved_for_exact_draft_once";
  human_review_required: false;
  action_closure_required: false;
}

export interface AuthorEmailReleaseState {
  draft_sha256: string;
  public_draft: false;
  eligible_for_human_approval: true;
  dispatch_authorized: boolean;
  human_approval_required: true;
  approval_status:
    | "pending_final_human_approval"
    | "approved_for_exact_draft_once";
}

interface DiagnosticAccuracyAggregate {
  mean: number;
  n: number;
  sample_sd: number;
  t95_interval: [number, number];
  values: number[];
}

export interface AccuracyPublicationBundle {
  schema_version: "nulspec-classification-accuracy-site-v1";
  publication_status: "ready";
  generated_at_utc: string;
  source: {
    repository: string;
    evidence_revision: string;
    handoff_path: string;
    handoff_sha256: string;
    handoff_schema_version: "nulspec-classification-accuracy-study-handoff-v1";
    source_publication_status: "blocked_pending_typed_accuracy_frontend";
    declared_artifact_count: number;
  };
  study: {
    id: string;
    slug: string;
    title: string;
    arxiv_id: string;
    arxiv_url: string;
    upstream_commit: string;
    scope: string;
  };
  metrics_schema: {
    id: "sprkd_trial_accuracy_v1";
    primary_unit: "percent_accuracy";
    primary_estimator: "final_sample_weighted_full_validation_accuracy";
    uncertainty: string;
    not_prompt_bootstrap: true;
    not_equivalence_test: true;
  };
  classification: {
    replication_outcome: "not_replicated";
    underlying_method_claim: "inconclusive";
    rationale: string;
    decision_source: string;
  };
  paper_reported_accuracy: Record<string, number>;
  primary: {
    metrics: Record<string, AccuracyMetricSummary>;
    comparisons: Record<string, AccuracyComparison>;
    runs: AccuracyRun[];
  };
  diagnostics: {
    preregistered_extensions: unknown;
    common_probe_hessian: unknown;
    posthoc_stability: {
      scope: string;
      aggregates: Record<string, unknown>;
      seeds: Record<string, Record<string, unknown>>;
    };
    posthoc_loss_contract: {
      scope: string;
      models: Record<
        string,
        { accuracy: DiagnosticAccuracyAggregate; cross_entropy: DiagnosticAccuracyAggregate }
      >;
      comparisons: Record<string, unknown>;
      runs: unknown[];
    };
  };
  compute: {
    recorded_device_process_hours_total: number;
    recorded_device_process_seconds: Record<string, number>;
    accounting_note: string;
  };
  artifacts: PublicationArtifact[];
  routes: {
    study: string;
    arms: string[];
  };
  extension_vote: AccuracyExtensionVote;
  final_peer_review: FinalPeerReviewState;
  author_email: AuthorEmailReleaseState;
  completion: {
    registered_runs: number;
    terminal_runs: number;
    claim_ready_runs: number;
    gates: Record<string, true>;
  };
  frozen_primary_result: {
    registered_runs: number;
    claim_ready_runs: number;
    may_be_rewritten_by_extension: false;
  };
}

export interface StudyArm extends PublicationArm {
  model_label: string;
  dataset_label: string;
  state: ArmState;
}

export interface StudyDocument extends Omit<PublicationBundle, "arms"> {
  metric_family: "reward_delta";
  study_id: string;
  state: StudyState;
  as_of_utc: string;
  arms: StudyArm[];
}

export interface AccuracyStudyArm extends AccuracyRun {
  ordinal: number;
  arm_id: string;
  state: ArmState;
}

export interface AccuracyStudyDocument extends AccuracyPublicationBundle {
  metric_family: "classification_accuracy";
  study_id: string;
  state: StudyState;
  as_of_utc: string;
  arms: AccuracyStudyArm[];
}

export type AnyStudyDocument = StudyDocument | AccuracyStudyDocument;

const publicationsDirectory = join(process.cwd(), "site-data", "publications");
let cachedStudies: AnyStudyDocument[] | undefined;

function armState(execution: PublicationArm["execution"]): ArmState {
  if (execution === "failed") return "FAILED";
  if (execution === "aborted") return "ABORTED";
  return "DONE";
}

function modelLabel(value: string) {
  const match = /^(pythia|smollm2)-(\d+m)$/i.exec(value);
  if (!match) return value.replaceAll("-", " ");
  const family = match[1].toLowerCase() === "pythia" ? "Pythia" : "SmolLM2";
  return `${family} ${match[2].toUpperCase()}`;
}

function datasetLabel(value: string) {
  const labels: Record<string, string> = {
    tinystories: "TinyStories",
    cnn_dailymail: "CNN / DailyMail",
    wikitext: "WikiText",
  };
  return labels[value] ?? value.replaceAll("_", " ");
}

function toStudy(bundle: PublicationBundle): StudyDocument {
  return {
    ...bundle,
    metric_family: "reward_delta",
    completion: {
      ...bundle.completion,
      tracks: bundle.completion.tracks.map((track) => ({
        ...track,
        label:
          track.label ??
          ({
            R: "Released-code path",
            M: "Manuscript-method bundle",
          }[track.id] ?? `Track ${track.id}`),
      })),
    },
    study_id: bundle.study.id,
    state: bundle.publication_status === "ready" ? "REPORTED" : "ANALYSIS-OPEN",
    as_of_utc: bundle.generated_at_utc,
    arms: bundle.arms.map((arm) => ({
      ...arm,
      model_label: modelLabel(arm.model),
      dataset_label: datasetLabel(arm.dataset),
      state: armState(arm.execution),
    })),
  };
}

function toAccuracyStudy(
  bundle: AccuracyPublicationBundle,
): AccuracyStudyDocument {
  return {
    ...bundle,
    metric_family: "classification_accuracy",
    study_id: bundle.study.id,
    state: "REPORTED",
    as_of_utc: bundle.generated_at_utc,
    arms: bundle.primary.runs.map((run, index) => ({
      ...run,
      ordinal: index + 1,
      arm_id: run.run_id,
      state: "DONE",
    })),
  };
}

export function isAccuracyStudy(
  study: AnyStudyDocument,
): study is AccuracyStudyDocument {
  return study.metric_family === "classification_accuracy";
}

export function getStudies(): AnyStudyDocument[] {
  if (cachedStudies) return cachedStudies;
  cachedStudies = readdirSync(publicationsDirectory)
    .filter((name) => /^study-[0-9]{3,}\.json$/.test(name))
    .map((name) => {
      const raw = readFileSync(join(publicationsDirectory, name), "utf8");
      const bundle = JSON.parse(raw) as
        | PublicationBundle
        | AccuracyPublicationBundle;
      if (bundle.schema_version === 1) return toStudy(bundle);
      if (bundle.schema_version === "nulspec-classification-accuracy-site-v1") {
        return toAccuracyStudy(bundle);
      }
      throw new Error(`Unsupported NULSPEC publication schema in ${name}`);
    })
    .sort(
      (left, right) =>
        Date.parse(right.as_of_utc) - Date.parse(left.as_of_utc) ||
        right.study_id.localeCompare(left.study_id),
    );
  return cachedStudies;
}

export function getStudy(id: string) {
  return getStudies().find((item) => item.study_id === id);
}

export function getStudyArm(studyId: string, armId: string) {
  const study = getStudy(studyId);
  if (!study) return undefined;
  const arm = study.arms.find((item) => item.arm_id === armId);
  if (!arm) return undefined;
  if (isAccuracyStudy(study)) {
    return {
      metric_family: "classification_accuracy" as const,
      study,
      arm: arm as AccuracyStudyArm,
    };
  }
  return {
    metric_family: "reward_delta" as const,
    study,
    arm: arm as StudyArm,
  };
}

export type ArmEvidenceFragment =
  | ""
  | "#comparison"
  | "#execution"
  | "#provenance"
  | "#evidence"
  | "#attempts";

export function armEvidenceUrl(
  studyId: string,
  armId: string,
  fragment: ArmEvidenceFragment = "",
) {
  return `/studies/${encodeURIComponent(studyId)}/arms/${encodeURIComponent(armId)}${fragment}`;
}

export function getLatestStudy() {
  const latest = getStudies()[0];
  if (!latest) throw new Error("NULSPEC has no published studies");
  return latest;
}

export function protocolUrl(study: AnyStudyDocument) {
  if (isAccuracyStudy(study)) {
    const protocol = study.artifacts.find(
      (artifact) => artifact.role === "frozen_primary_protocol",
    );
    return protocol ? artifactUrl(protocol) : study.study.arxiv_url;
  }
  return `${GITHUB_URL}/blob/main/protocols/${study.study.paper.arxiv_id}/REPRODUCTION_PROTOCOL.md`;
}

export function artifactUrl(artifact: PublicationArtifact) {
  return `/${artifact.public_path}`;
}

export function classificationLabel(value: Classification) {
  return value.replaceAll("_", " ").toLowerCase();
}

export function studyClassificationLabel(study: AnyStudyDocument) {
  return isAccuracyStudy(study)
    ? study.classification.replication_outcome.replaceAll("_", " ")
    : classificationLabel(study.verdict.classification);
}

export function studySummary(study: AnyStudyDocument) {
  return isAccuracyStudy(study)
    ? study.classification.rationale
    : study.verdict.summary;
}

export const stateMeta: Record<
  ArmState,
  { glyph: string; label: string; explanation: string }
> = {
  QUEUED: {
    glyph: "○",
    label: "Queued",
    explanation: "Assigned, not yet started",
  },
  RUNNING: {
    glyph: "●",
    label: "Running",
    explanation: "Actively executing; no result implied",
  },
  DONE: {
    glyph: "■",
    label: "Done",
    explanation: "Selected run is terminal and claim-ready",
  },
  FAILED: {
    glyph: "×",
    label: "Failed",
    explanation: "Selected run ended without a valid completion",
  },
  ABORTED: {
    glyph: "□",
    label: "Aborted",
    explanation: "Selected run was stopped deliberately and retained",
  },
};

export function studyCounts(arms: Array<{ state: ArmState }>) {
  return arms.reduce<Record<ArmState, number>>(
    (counts, arm) => {
      counts[arm.state] += 1;
      return counts;
    },
    { QUEUED: 0, RUNNING: 0, DONE: 0, FAILED: 0, ABORTED: 0 },
  );
}

export function formatAsOf(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

export function formatSigned(value: number) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(4)}`;
}

export function formatPValue(value: number) {
  if (value > 0 && value < 0.0001) return value.toExponential(2);
  return value.toFixed(4);
}
