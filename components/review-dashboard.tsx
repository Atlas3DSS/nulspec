"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { NulspecMark } from "@/components/nulspec-mark";
import type {
  HumanDecision,
  ReviewInbox,
  ReviewSession,
  ReviewTask,
} from "@/lib/review";

type InboxFilter = "needs-review" | "email" | "completed" | "all";
type GateName = "publication" | "author_email";

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "UTC",
});

function formatDate(value: string) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf()) ? value : `${dateFormatter.format(parsed)} UTC`;
}

function formatMoney(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 6,
  }).format(value);
}

function statusLabel(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function shortHash(value: string) {
  return `${value.slice(0, 12)}…${value.slice(-8)}`;
}

function downloadRecord(decision: HumanDecision) {
  const blob = new Blob([`${JSON.stringify(decision.record, null, 2)}\n`], {
    type: "application/json",
  });
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.download = `${decision.task_id}-${decision.gate}-${decision.decision_id}.json`;
  anchor.click();
  URL.revokeObjectURL(href);
}

function DecisionSummary({ decision }: { decision: HumanDecision }) {
  return (
    <div className="review-decision-summary">
      <div>
        <span className="review-state review-state--complete">
          {statusLabel(decision.decision)}
        </span>
        <p>
          Recorded by <strong>{decision.reviewer_display_name}</strong> on{" "}
          {formatDate(decision.decided_at)}.
        </p>
      </div>
      <p>{decision.notes}</p>
      <dl className="review-hash-list">
        <div>
          <dt>Decision ID</dt>
          <dd><code>{decision.decision_id}</code></dd>
        </div>
        <div>
          <dt>Record SHA-256</dt>
          <dd title={decision.record_sha256}><code>{shortHash(decision.record_sha256)}</code></dd>
        </div>
        <div>
          <dt>Task binding</dt>
          <dd title={decision.binding_sha256}><code>{shortHash(decision.binding_sha256)}</code></dd>
        </div>
      </dl>
      <button
        className="review-text-button"
        onClick={() => downloadRecord(decision)}
        type="button"
      >
        Download machine decision
      </button>
    </div>
  );
}

function GateDecisionForm({
  task,
  gate,
  csrfToken,
  onRecorded,
}: {
  task: ReviewTask;
  gate: GateName;
  csrfToken: string;
  onRecorded: (message: string) => Promise<void>;
}) {
  const [decision, setDecision] = useState("");
  const [notes, setNotes] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const prefix = `${task.task_id}-${gate}`;
  const options =
    gate === "publication"
      ? [
          {
            value: "APPROVE_RELEASE",
            label: "Approve this release",
            detail:
              "Accept this exact evidence packet for publication. The frozen scientific result does not change.",
          },
          {
            value: "KEEP_BLOCKED",
            label: "Keep publication blocked",
            detail:
              "Return the release to research. A changed packet must enter as a new immutable task.",
          },
        ]
      : [
          {
            value: "APPROVE_SEND",
            label: "Approve exact draft",
            detail:
              "Authorize this draft and recipient list for later operator dispatch. This button does not send it.",
          },
          {
            value: "RETURN_FOR_REVISION",
            label: "Return email for revision",
            detail:
              "Reject this exact draft. A revision must receive a new hash and a new review task.",
          },
        ];

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await fetch(
        `/api/review/tasks/${encodeURIComponent(task.task_id)}/decisions`,
        {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-Nulspec-CSRF": csrfToken,
          },
          body: JSON.stringify({
            gate,
            decision,
            notes,
            binding_sha256: task.packet_sha256,
            confirmed,
          }),
        },
      );
      const payload = (await response.json().catch(() => ({}))) as {
        error?: string;
        message?: string;
      };
      if (response.status === 401) {
        window.location.replace("/review/login");
        return;
      }
      if (!response.ok) {
        setError(
          payload.message ||
            (payload.error === "already_decided"
              ? "Another reviewer already recorded this decision. Reload the inbox."
              : "The decision was not recorded. Review the fields and try again."),
        );
        return;
      }
      setDecision("");
      setNotes("");
      setConfirmed(false);
      await onRecorded(
        gate === "publication"
          ? "Publication disposition recorded."
          : "Author-email disposition recorded; no email was sent.",
      );
    } catch {
      setError("The private review service could not be reached. No decision was recorded.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="review-decision-form" onSubmit={submit}>
      <fieldset disabled={busy}>
        <legend>Record one final human decision</legend>
        <div className="review-decision-options">
          {options.map((option) => (
            <label className="review-decision-option" key={option.value}>
              <input
                checked={decision === option.value}
                name={`${prefix}-decision`}
                onChange={() => setDecision(option.value)}
                required
                type="radio"
                value={option.value}
              />
              <span>
                <strong>{option.label}</strong>
                <small>{option.detail}</small>
              </span>
            </label>
          ))}
        </div>
        <label className="review-notes-label" htmlFor={`${prefix}-notes`}>
          Decision rationale
          <span>20–4,000 characters · retained with the machine record</span>
        </label>
        <textarea
          id={`${prefix}-notes`}
          maxLength={4000}
          minLength={20}
          onChange={(event) => setNotes(event.target.value)}
          placeholder="State what you checked and why this disposition is appropriate."
          required
          rows={4}
          value={notes}
        />
        <label className="review-confirmation">
          <input
            checked={confirmed}
            onChange={(event) => setConfirmed(event.target.checked)}
            required
            type="checkbox"
          />
          <span>
            I reviewed the evidence bound to task <code>{shortHash(task.packet_sha256)}</code>{" "}
            and understand this decision cannot be overwritten.
          </span>
        </label>
        <button className="button button--primary" disabled={busy} type="submit">
          {busy ? "Recording…" : "Record final decision"}
        </button>
      </fieldset>
      <p className="review-form-error" role="alert">{error}</p>
    </form>
  );
}

function PublicationGate({
  task,
  csrfToken,
  onRecorded,
}: {
  task: ReviewTask;
  csrfToken: string;
  onRecorded: (message: string) => Promise<void>;
}) {
  const gate = task.publication_gate;
  return (
    <section className="review-gate" aria-labelledby={`${task.task_id}-publication`}>
      <div className="review-gate__header">
        <div>
          <p className="section-kicker">Gate 01</p>
          <h3 id={`${task.task_id}-publication`}>Publication disposition</h3>
        </div>
        <span className={`review-state review-state--${gate.status}`}>
          {statusLabel(gate.status)}
        </span>
      </div>
      <p className="review-gate__question">{gate.question}</p>
      <p>{gate.reason}</p>
      <p className="review-gate__boundary">
        This is release governance. It cannot edit a result, metric, protocol,
        classification, or author claim.
      </p>
      {gate.decision ? (
        <DecisionSummary decision={gate.decision} />
      ) : gate.action_allowed ? (
        <GateDecisionForm
          csrfToken={csrfToken}
          gate="publication"
          onRecorded={onRecorded}
          task={task}
        />
      ) : null}
    </section>
  );
}

function EmailGate({
  task,
  csrfToken,
  onRecorded,
}: {
  task: ReviewTask;
  csrfToken: string;
  onRecorded: (message: string) => Promise<void>;
}) {
  const gate = task.author_email_gate;
  const blockedMessage =
    gate.status === "blocked_by_publication"
      ? "The draft is visible for context, but its decision remains locked until publication is approved."
      : gate.status === "blocked_missing_recipients"
        ? "Publication is approved, but the recipient list is empty. Import a new hash-bound task with recipients before approving dispatch."
        : null;
  return (
    <section className="review-gate" aria-labelledby={`${task.task_id}-email`}>
      <div className="review-gate__header">
        <div>
          <p className="section-kicker">Gate 02</p>
          <h3 id={`${task.task_id}-email`}>Author email</h3>
        </div>
        <span className={`review-state review-state--${gate.status}`}>
          {statusLabel(gate.status)}
        </span>
      </div>
      {blockedMessage && <p className="review-gate__blocked">{blockedMessage}</p>}
      <div className="review-email-envelope">
        <dl>
          <div>
            <dt>To</dt>
            <dd>
              {gate.recipients.length > 0
                ? gate.recipients
                    .map((recipient) => `${recipient.name} <${recipient.email}>`)
                    .join(", ")
                : "No recipients bound"}
            </dd>
          </div>
          <div>
            <dt>Subject</dt>
            <dd>{gate.subject}</dd>
          </div>
          <div>
            <dt>Draft SHA-256</dt>
            <dd title={gate.draft_sha256}><code>{shortHash(gate.draft_sha256)}</code></dd>
          </div>
        </dl>
        <details open={gate.status === "awaiting_human"}>
          <summary>Read exact email draft</summary>
          <pre>{gate.body}</pre>
        </details>
      </div>
      <p className="review-gate__boundary">
        Approval authorizes only this exact draft and recipient list for later
        operator dispatch. It does not send email.
      </p>
      {gate.decision ? (
        <DecisionSummary decision={gate.decision} />
      ) : gate.action_allowed ? (
        <GateDecisionForm
          csrfToken={csrfToken}
          gate="author_email"
          onRecorded={onRecorded}
          task={task}
        />
      ) : null}
    </section>
  );
}

function ReviewTaskCard({
  task,
  csrfToken,
  onRecorded,
}: {
  task: ReviewTask;
  csrfToken: string;
  onRecorded: (message: string) => Promise<void>;
}) {
  return (
    <article
      className={`review-task${task.superseded_by ? " review-task--superseded" : ""}`}
      data-review-task={task.task_id}
    >
      {task.superseded_by && (
        <div className="review-task__superseded" role="status">
          <strong>Historical packet — actions disabled.</strong>
          <span>
            Superseded by task <code>{task.superseded_by}</code>. Review the newer
            immutable packet instead.
          </span>
        </div>
      )}
      <header className="review-task__header">
        <div>
          <div className="review-task__labels">
            <span className={`review-priority review-priority--${task.priority}`}>
              {task.priority} priority
            </span>
            <span>Study {task.study.study_id}</span>
            <span>arXiv:{task.study.arxiv_id}</span>
          </div>
          <h2>{task.study.paper_title}</h2>
          <p>{task.queued_reason}</p>
        </div>
        <dl className="review-task__outcomes">
          <div>
            <dt>Replication</dt>
            <dd>{task.study.replication_assessment}</dd>
          </div>
          <div>
            <dt>Method</dt>
            <dd>{task.study.method_assessment}</dd>
          </div>
        </dl>
      </header>

      <div className="review-task__integrity">
        <span>Immutable task</span>
        <code title={task.packet_sha256}>{task.packet_sha256}</code>
      </div>

      <div className="review-context-grid">
        <details className="review-context" open>
          <summary>Research brief</summary>
          <pre>{task.brief}</pre>
        </details>
        <details className="review-context">
          <summary>Evidence packet · {task.evidence.length} items</summary>
          <ul className="review-evidence-list">
            {task.evidence.map((item) => (
              <li key={item.id}>
                <div>
                  <span>{item.kind}</span>
                  <a href={item.url} rel="noreferrer" target="_blank">
                    {item.label} ↗
                  </a>
                </div>
                <p>{item.summary}</p>
                <code title={item.sha256}>{shortHash(item.sha256)}</code>
              </li>
            ))}
          </ul>
        </details>
        <details className="review-context review-context--wide">
          <summary>
            External review events · {task.review_events.length} ·{" "}
            {formatMoney(task.review_cost_total_usd)} total
          </summary>
          <div className="review-event-list">
            {task.review_events.map((event) => (
              <article key={event.event_id}>
                <div className="review-event__topline">
                  <strong>{event.reviewer}</strong>
                  <span>{formatMoney(event.cost_usd)}</span>
                </div>
                <p className="review-event__model">{event.provider} · {event.model}</p>
                <dl>
                  <div><dt>Outcome</dt><dd>{statusLabel(event.outcome)}</dd></div>
                  <div><dt>Validation</dt><dd>{statusLabel(event.validation)}</dd></div>
                  <div>
                    <dt>Consensus</dt>
                    <dd>{event.consensus_eligible ? "Eligible" : "Not eligible"}</dd>
                  </div>
                </dl>
                <p>{event.summary}</p>
                <p className="review-event__trace" title={event.trace_sha256}>
                  Trace SHA-256 <code>{shortHash(event.trace_sha256)}</code>
                </p>
              </article>
            ))}
          </div>
        </details>
      </div>

      <div className="review-task__links">
        <a href={task.study.paper_url} rel="noreferrer" target="_blank">Read paper ↗</a>
        <a href={task.source.repository_url} rel="noreferrer" target="_blank">Repository ↗</a>
        {task.source.pull_request_url && (
          <a href={task.source.pull_request_url} rel="noreferrer" target="_blank">
            Review pull request ↗
          </a>
        )}
      </div>

      <div className="review-gates">
        <PublicationGate csrfToken={csrfToken} onRecorded={onRecorded} task={task} />
        <EmailGate csrfToken={csrfToken} onRecorded={onRecorded} task={task} />
      </div>
    </article>
  );
}

export function ReviewDashboard() {
  const [session, setSession] = useState<ReviewSession | null>(null);
  const [inbox, setInbox] = useState<ReviewInbox | null>(null);
  const [filter, setFilter] = useState<InboxFilter>("needs-review");
  const [status, setStatus] = useState("Loading the private review inbox…");
  const [error, setError] = useState("");
  const [signingOut, setSigningOut] = useState(false);

  const refreshInbox = useCallback(async () => {
    const response = await fetch("/api/review/tasks", {
      cache: "no-store",
      credentials: "same-origin",
    });
    if (response.status === 401) {
      window.location.replace("/review/login");
      throw new Error("session expired");
    }
    if (!response.ok) throw new Error("inbox unavailable");
    const payload = (await response.json()) as ReviewInbox;
    setInbox(payload);
  }, []);

  useEffect(() => {
    let current = true;
    async function load() {
      try {
        const response = await fetch("/api/review/session", {
          cache: "no-store",
          credentials: "same-origin",
        });
        if (response.status === 401) {
          window.location.replace("/review/login");
          return;
        }
        if (!response.ok) throw new Error("session unavailable");
        const activeSession = (await response.json()) as ReviewSession;
        if (!current) return;
        setSession(activeSession);
        await refreshInbox();
        if (!current) return;
        setStatus("Review inbox loaded.");
      } catch {
        if (!current) return;
        setError("The private review inbox could not be loaded. No action is available.");
        setStatus("");
      }
    }
    void load();
    return () => {
      current = false;
    };
  }, [refreshInbox]);

  const filteredTasks = useMemo(() => {
    if (!inbox) return [];
    if (filter === "all") return inbox.tasks;
    if (filter === "completed") return inbox.tasks.filter((task) => task.complete);
    if (filter === "email") {
      return inbox.tasks.filter(
        (task) =>
          !task.superseded_by &&
          task.author_email_gate.status === "awaiting_human",
      );
    }
    return inbox.tasks.filter(
      (task) =>
        !task.superseded_by &&
        (task.publication_gate.status === "awaiting_human" ||
          task.author_email_gate.status === "awaiting_human"),
    );
  }, [filter, inbox]);

  async function recorded(message: string) {
    await refreshInbox();
    setStatus(message);
  }

  async function logout() {
    if (!session) return;
    setSigningOut(true);
    try {
      await fetch("/api/review/logout", {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-Nulspec-CSRF": session.csrf_token },
      });
    } finally {
      window.location.replace("/review/login");
    }
  }

  return (
    <div className="review-workspace">
      <header className="review-workspace-header">
        <div className="review-workspace-header__inner">
          <Link className="wordmark" href="/" aria-label="NULSPEC home">
            <NulspecMark className="wordmark__mark" />
            <span>NUL</span>
            <span className="wordmark__accent">SPEC</span>
          </Link>
          <div className="review-workspace-header__session">
            <span>
              {session ? `Signed in as ${session.reviewer.display_name}` : "Authenticating…"}
            </span>
            <button disabled={!session || signingOut} onClick={logout} type="button">
              {signingOut ? "Signing out…" : "Sign out"}
            </button>
          </div>
        </div>
      </header>

      <main id="main-content">
        <section className="review-inbox-hero">
          <div className="review-shell review-inbox-hero__grid">
            <div>
              <p className="section-kicker">Private release governance</p>
              <h1>Human review inbox</h1>
              <p>
                Every item carries its blocking reason, evidence, reviewer history,
                exact email draft, costs, immutable hashes, and final actions. Human
                decisions govern release; they never rewrite scientific evidence.
              </p>
            </div>
            <aside>
              <span>Fail-closed workflow</span>
              <p>Publication → exact email approval → operator dispatch</p>
              <small>No dashboard action deploys a study or sends mail automatically.</small>
            </aside>
          </div>
        </section>

        <div className="review-shell">
          <p className="review-dashboard-status" role="status">{status}</p>
          {error && <p className="review-dashboard-error" role="alert">{error}</p>}

          {inbox && (
            <>
              <section className="review-summary" aria-label="Review queue summary">
                <article>
                  <span>Publication</span>
                  <strong>{inbox.summary.papers_waiting}</strong>
                  <p>papers awaiting human disposition</p>
                </article>
                <article>
                  <span>Email</span>
                  <strong>{inbox.summary.emails_waiting}</strong>
                  <p>exact drafts ready for approval</p>
                </article>
                <article>
                  <span>Blocked email</span>
                  <strong>{inbox.summary.emails_blocked}</strong>
                  <p>downstream drafts not yet actionable</p>
                </article>
                <article>
                  <span>Complete</span>
                  <strong>{inbox.summary.completed_tasks}</strong>
                  <p>tasks with final recorded dispositions</p>
                </article>
              </section>

              <section className="review-inbox" aria-labelledby="review-inbox-title">
                <div className="review-inbox__toolbar">
                  <div>
                    <p className="section-kicker">Decision queue</p>
                    <h2 id="review-inbox-title">Items requiring attention</h2>
                  </div>
                  <div className="review-filter" aria-label="Filter review tasks">
                    {(
                      [
                        ["needs-review", "Needs review"],
                        ["email", "Email"],
                        ["completed", "Completed"],
                        ["all", "All"],
                      ] as const
                    ).map(([value, label]) => (
                      <button
                        aria-pressed={filter === value}
                        key={value}
                        onClick={() => setFilter(value)}
                        type="button"
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="review-task-list">
                  {filteredTasks.map((task) => (
                    <ReviewTaskCard
                      csrfToken={session?.csrf_token ?? ""}
                      key={task.task_id}
                      onRecorded={recorded}
                      task={task}
                    />
                  ))}
                  {filteredTasks.length === 0 && (
                    <div className="review-empty-state">
                      <span aria-hidden="true">✓</span>
                      <h3>No items in this view</h3>
                      <p>The queue is current. Use another filter to inspect blocked or completed work.</p>
                    </div>
                  )}
                </div>
              </section>

              <section className="review-activity" aria-labelledby="review-activity-title">
                <div>
                  <p className="section-kicker">Append-only history</p>
                  <h2 id="review-activity-title">Recent queue activity</h2>
                </div>
                {inbox.recent_activity.length > 0 ? (
                  <ol>
                    {inbox.recent_activity.map((item, index) => (
                      <li key={`${item.created_at}-${item.event_type}-${index}`}>
                        <span>{formatDate(item.created_at)}</span>
                        <strong>{statusLabel(item.event_type)}</strong>
                        <p>
                          {item.task_id ? `Task ${item.task_id}` : "Inbox"}
                          {item.username ? ` · ${item.username}` : ""}
                          {typeof item.detail.decision === "string"
                            ? ` · ${statusLabel(item.detail.decision)}`
                            : ""}
                        </p>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p>No task or decision events have been recorded yet.</p>
                )}
              </section>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
