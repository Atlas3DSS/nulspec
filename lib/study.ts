import studyDocument from "@/site-data/study-001.json";

export const NOMINATE_URL =
  "https://github.com/Atlas3DSS/nulspec/issues/new?template=replication-request.yml";
export const KOFI_URL = "https://ko-fi.com/monkeymind101";
export const GITHUB_URL = "https://github.com/Atlas3DSS/nulspec";
export const PROTOCOL_URL =
  `${GITHUB_URL}/blob/main/protocols/2607.25091/REPRODUCTION_PROTOCOL.md`;

export type ArmState = "QUEUED" | "RUNNING" | "DONE" | "FAILED" | "ABORTED";
export type Provenance = "EXACT" | "COMPAT";
export type Verdict = "MATCH" | "DIVERGES" | "INCONCLUSIVE" | null;

export interface StudyArm {
  ordinal: number;
  arm_id: string;
  model: string;
  dataset: string;
  gpu: string;
  host: string;
  provenance: Provenance;
  state: ArmState;
  verdict: Verdict;
}

export interface Deviation {
  id: string;
  scope: string;
  what: string;
  impact_control: string;
}

export interface StudyDocument {
  schema_version: number;
  study_id: string;
  state: "SPEC-FROZEN" | "RUNNING" | "RUNS-COMPLETE" | "ANALYSIS-OPEN" | "REPORTED";
  as_of_utc: string;
  paper: {
    title: string;
    arxiv_id: string;
    url: string;
    source_commit: string;
  };
  protocol: {
    version: string;
    tag: string;
    freeze_commit: string;
    matrix_sha256: string;
    config_sha256: string;
  };
  claim_under_test: string;
  arms: StudyArm[];
  deviations: Deviation[];
}

export const study = studyDocument as StudyDocument;

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
    explanation: "Run finished; no study verdict implied",
  },
  FAILED: {
    glyph: "×",
    label: "Failed",
    explanation: "Run ended without a valid completion",
  },
  ABORTED: {
    glyph: "□",
    label: "Aborted",
    explanation: "Stopped deliberately and retained",
  },
};

export function studyCounts(arms: StudyArm[] = study.arms) {
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
