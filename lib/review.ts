export type ReviewerIdentity = {
  username: string;
  display_name: string;
};

export type ReviewSession = {
  ok: true;
  reviewer: ReviewerIdentity;
  csrf_token: string;
  expires_at: string;
};

export type ReviewEvidence = {
  id: string;
  label: string;
  kind: string;
  url: string;
  sha256: string;
  summary: string;
};

export type ExternalReviewEvent = {
  event_id: string;
  reviewer: string;
  provider: string;
  model: string;
  outcome: string;
  validation: string;
  summary: string;
  cost_usd: number;
  trace_sha256: string;
  consensus_eligible: boolean;
};

export type HumanDecision = {
  decision_id: string;
  task_id: string;
  gate: "publication" | "author_email";
  decision: string;
  reviewer_username: string;
  reviewer_display_name: string;
  notes: string;
  binding_sha256: string;
  record_sha256: string;
  record: Record<string, unknown>;
  decided_at: string;
};

type ReviewSourceBase = {
  source_revision: string;
  repository_url: string;
  pull_request_url: string | null;
  review_packet_sha256: string;
};

type CurrentReviewSource = ReviewSourceBase & {
  release_review_consensus_sha256: string;
};

type LegacyReviewSource = ReviewSourceBase & {
  final_peer_review_sha256: string;
  supplemental_review_consensus_sha256: string | null;
  fable_action_closure_sha256: string | null;
};

export type ReviewTask = {
  task_id: string;
  supersedes_task_id: string | null;
  superseded_by: string | null;
  packet_sha256: string;
  imported_at: string;
  priority: "normal" | "high" | "urgent";
  queued_reason: string;
  submitted_at_utc: string;
  study: {
    study_id: string;
    paper_title: string;
    paper_url: string;
    arxiv_id: string;
    replication_assessment: string;
    method_assessment: string;
  };
  source: CurrentReviewSource | LegacyReviewSource;
  brief: string;
  evidence: ReviewEvidence[];
  review_events: ExternalReviewEvent[];
  review_cost_total_usd: number;
  publication_gate: {
    reason: string;
    question: string;
    status: "awaiting_human" | "approved" | "kept_blocked";
    action_allowed: boolean;
    decision: HumanDecision | null;
  };
  author_email_gate: {
    subject: string;
    body: string;
    draft_sha256: string;
    recipients: Array<{ name: string; email: string }>;
    status:
      | "blocked_by_publication"
      | "blocked_missing_recipients"
      | "awaiting_human"
      | "approved_for_operator_dispatch"
      | "returned_for_revision";
    action_allowed: boolean;
    decision: HumanDecision | null;
  };
  complete: boolean;
  decisions: HumanDecision[];
};

export type ReviewInbox = {
  ok: true;
  schema_version: string;
  summary: {
    papers_waiting: number;
    emails_waiting: number;
    emails_blocked: number;
    completed_tasks: number;
    total_tasks: number;
  };
  tasks: ReviewTask[];
  recent_activity: Array<{
    event_type: string;
    username: string | null;
    task_id: string | null;
    gate: string | null;
    detail: Record<string, unknown>;
    created_at: string;
  }>;
};
