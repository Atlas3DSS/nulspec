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

export interface StudyArm extends PublicationArm {
  model_label: string;
  dataset_label: string;
  state: ArmState;
}

export interface StudyDocument extends Omit<PublicationBundle, "arms"> {
  study_id: string;
  state: StudyState;
  as_of_utc: string;
  arms: StudyArm[];
}

const publicationsDirectory = join(process.cwd(), "site-data", "publications");
let cachedStudies: StudyDocument[] | undefined;

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

export function getStudies(): StudyDocument[] {
  if (cachedStudies) return cachedStudies;
  cachedStudies = readdirSync(publicationsDirectory)
    .filter((name) => /^study-[0-9]{3,}\.json$/.test(name))
    .map((name) => {
      const raw = readFileSync(join(publicationsDirectory, name), "utf8");
      return toStudy(JSON.parse(raw) as PublicationBundle);
    })
    .sort((left, right) => right.study_id.localeCompare(left.study_id));
  return cachedStudies;
}

export function getStudy(id: string) {
  return getStudies().find((item) => item.study_id === id);
}

export function getStudyArm(studyId: string, armId: string) {
  const study = getStudy(studyId);
  if (!study) return undefined;
  const arm = study.arms.find((item) => item.arm_id === armId);
  return arm ? { study, arm } : undefined;
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

export function protocolUrl(study: StudyDocument) {
  return `${GITHUB_URL}/blob/main/protocols/${study.study.paper.arxiv_id}/REPRODUCTION_PROTOCOL.md`;
}

export function artifactUrl(artifact: PublicationArtifact) {
  return `/${artifact.public_path}`;
}

export function classificationLabel(value: Classification) {
  return value.replaceAll("_", " ").toLowerCase();
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

export function studyCounts(arms: StudyArm[]) {
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
