"use client";

import { useCallback, useEffect, useState } from "react";
import styles from "./acts.module.css";

type RunStatus = "queued" | "running" | "done" | "skipped";
type OwnerStatus = "unsent" | "approved" | "sent" | "replied";
type Decision = "approve" | "hold" | "decline" | "sent" | "replied";

export type Act = {
  id: string;
  slug: string;
  repo: string;
  repo_url: string;
  issue_url: string;
  issue_number: string;
  licence: string;
  commit: string;
  status: RunStatus;
  gpu: string;
  gpu_minutes: number | null;
  wall_minutes: number | null;
  started: string | null;
  finished: string | null;
  headline: string;
  headline_items: string[];
  owner_status: OwnerStatus;
  report_path: string | null;
  report_sha256: string | null;
  // owner view only
  host?: string;
  follow_on?: string;
  notes?: string;
  message_draft?: string;
  public_report_url?: string;
  owner_decision?: Decision | null;
  owner_decision_at?: string | null;
  owner_decision_note?: string;
  on_public_site?: boolean;
};

type QueueItem = {
  slug: string;
  repo: string;
  issue_url: string;
  licence: string;
  stars: number | null;
  evidence_quote: string;
  data_terms: string;
  vram_gb: number | null;
};

export type ActsDoc = {
  schema_version: string;
  generated_at: string;
  stats: { acts_done: number; gpu_hours: number; approvals: number; replies: number; running: number; queued: number };
  acts: Act[];
  queue?: QueueItem[];
  skipped?: { slug: string; repo: string; issue_url: string; licence: string; reason: string }[];
  csrf?: string;
};

const statementUrl =
  "https://terrytao.wordpress.com/2026/10/07/ahm-statement-on-openais-october-6-release-of-mathematical-documents/";
// Owner has not supplied the tip-jar link yet; set it here (https URL) when he does. No eth address until confirmed.
const tipJarUrl = "";

const day = (iso: string | null) => (iso ? iso.slice(0, 10) : "date pending");
const mins = (m: number | null) => (m == null ? "pending" : m >= 90 ? `${(m / 60).toFixed(1)} h` : `${m} min`);

function Chip({ kind, children }: { kind: string; children: React.ReactNode }) {
  return <span className={`${styles.chip} ${styles[`chip_${kind}`] ?? ""}`}>{children}</span>;
}

function copyText(text: string): Promise<void> {
  if (navigator.clipboard?.writeText) return navigator.clipboard.writeText(text);
  return new Promise((resolve, reject) => {
    const area = document.createElement("textarea");
    area.value = text;
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    try {
      if (document.execCommand("copy")) resolve();
      else reject(new Error("copy refused"));
    } catch (error) {
      reject(error);
    } finally {
      area.remove();
    }
  });
}

function DraftBox({ text }: { text: string }) {
  const [state, setState] = useState<"idle" | "copied" | "failed">("idle");
  return (
    <div className={styles.draft}>
      <div className={styles.draftHead}>
        <strong>Message draft</strong>
        <Chip kind="unsent">not sent</Chip>
        <button
          type="button"
          className={styles.btn}
          onClick={() =>
            copyText(text).then(
              () => setState("copied"),
              () => setState("failed"),
            )
          }
        >
          {state === "copied" ? "Copied" : state === "failed" ? "Select and copy by hand" : "Copy message"}
        </button>
      </div>
      <textarea readOnly rows={Math.min(26, text.split("\n").reduce((n, l) => n + Math.max(1, Math.ceil(l.length / 66)), 1))} value={text} aria-label="Unsent message draft" />
    </div>
  );
}

function Actions({ act, onDecide, busy }: { act: Act; onDecide: (id: string, d: Decision, note: string) => void; busy: boolean }) {
  const [note, setNote] = useState("");
  const current = act.owner_decision;
  const btn = (d: Decision, label: string, tone: string) => (
    <button
      type="button"
      disabled={busy}
      aria-pressed={current === d}
      className={`${styles.btn} ${styles[`btn_${tone}`]} ${current === d ? styles.btnOn : ""}`}
      onClick={() => onDecide(act.id, d, note)}
    >
      {label}
    </button>
  );
  return (
    <div className={styles.actions}>
      <div className={styles.actionRow}>
        {btn("approve", "Approve", "go")}
        {btn("hold", "Hold", "wait")}
        {btn("decline", "Decline", "stop")}
        {act.owner_status === "approved" && btn("sent", "I sent it", "plain")}
        {act.owner_status === "sent" && btn("replied", "They replied", "plain")}
        <input
          type="text"
          maxLength={300}
          placeholder="Optional note for the record"
          aria-label="Optional note"
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
      </div>
      <p className={styles.fine}>
        {current
          ? `Recorded: ${current}${act.owner_decision_at ? ` at ${act.owner_decision_at.slice(0, 16).replace("T", " ")} UTC` : ""}${act.owner_decision_note ? ` (${act.owner_decision_note})` : ""}. `
          : "No decision recorded yet. "}
        Approve only marks the act ready for you to send; this page never sends anything.
      </p>
    </div>
  );
}

function ActCard({ act, owner, onDecide, busy }: { act: Act; owner: boolean; onDecide: (id: string, d: Decision, note: string) => void; busy: boolean }) {
  return (
    <article className={styles.card} id={act.slug}>
      <header className={styles.cardHead}>
        <div>
          <h2>
            <a href={act.repo_url} rel="noreferrer">{act.repo}</a>
          </h2>
          <p className={styles.sub}>
            <a href={act.issue_url} rel="noreferrer">issue #{act.issue_number}</a>
            <span> · {act.licence} · commit {act.commit || "n/a"} · {day(act.finished ?? act.started)}</span>
          </p>
        </div>
        <div className={styles.chips}>
          <Chip kind={act.status}>{act.status}</Chip>
          <Chip kind={act.owner_status}>{act.owner_status}</Chip>
          {owner && act.owner_decision === "hold" && <Chip kind="hold">on hold</Chip>}
          {owner && act.owner_decision === "decline" && <Chip kind="decline">declined</Chip>}
          {owner && !act.on_public_site && <Chip kind="private">not on public site</Chip>}
        </div>
      </header>

      <dl className={styles.facts}>
        <div><dt>What we ran</dt><dd>{act.gpu}, {mins(act.gpu_minutes)} of GPU time, {mins(act.wall_minutes)} wall{owner && act.host ? ` (${act.host})` : ""}</dd></div>
        <div><dt>Report</dt><dd>{act.report_path ? <a href={act.report_path}>REPORT.md</a> : "pending"}</dd></div>
      </dl>

      <section aria-label="Headline numbers">
        <h3>Headline numbers</h3>
        <ol className={styles.numbers}>
          {act.headline_items.map((item, i) => <li key={i}>{item}</li>)}
        </ol>
        {act.headline_items.length === 0 ? <p className={styles.fine}>{act.status === "running" ? "Running now; numbers appear when the run finishes." : "No numbers recorded yet."}</p> : null}
      </section>

      {owner && (
        <>
          <section aria-label="Proposed follow-on">
            <h3>Proposed follow-on (private)</h3>
            <p>{act.follow_on || "None recorded."}</p>
            {act.notes ? <p className={styles.fine}>Notes: {act.notes}</p> : null}
          </section>
          {act.status === "done" ? (
            <>
              {act.message_draft && <DraftBox text={act.message_draft} />}
              <Actions act={act} onDecide={onDecide} busy={busy} />
            </>
          ) : (
            <p className={styles.fine}>The draft and your decision appear here when the run is done.</p>
          )}
        </>
      )}
    </article>
  );
}

export function ActsDashboard({ initial }: { initial: ActsDoc }) {
  const [ownerDoc, setOwnerDoc] = useState<ActsDoc | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const fetchOwner = useCallback(async (): Promise<ActsDoc | null> => {
    try {
      const res = await fetch("/api/acts/private", { cache: "no-store", credentials: "same-origin" });
      if (!res.ok) return null;
      const body = await res.json();
      return body?.schema_version === initial.schema_version ? (body as ActsDoc) : null;
    } catch {
      return null; // public site: no owner API, stay in public view
    }
  }, [initial.schema_version]);

  useEffect(() => {
    let live = true;
    void fetchOwner().then((doc) => {
      if (live && doc) setOwnerDoc(doc);
    });
    return () => {
      live = false;
    };
  }, [fetchOwner]);

  const decide = async (actId: string, decision: Decision, note: string) => {
    if (!ownerDoc?.csrf) return;
    setBusy(true);
    setError("");
    try {
      const res = await fetch("/api/acts/decision", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-Acts-Csrf": ownerDoc.csrf },
        body: JSON.stringify({ act_id: actId, decision, note }),
      });
      if (!res.ok) throw new Error(`decision rejected (${res.status})`);
      const doc = await fetchOwner();
      if (doc) setOwnerDoc(doc);
    } catch (e) {
      setError(e instanceof Error ? e.message : "decision failed");
    } finally {
      setBusy(false);
    }
  };

  const owner = ownerDoc !== null;
  const doc = ownerDoc ?? initial;
  const pending = doc.acts.filter((a) => a.status === "done" && a.owner_status === "unsent" && !a.owner_decision).length;

  return (
    <div className={styles.shell}>
      <section className={styles.hero}>
        <p className={styles.eyebrow}>Independent / experimental</p>
        <h1>Random acts of science</h1>
        <section className={styles.about} aria-labelledby="about-heading">
          <h2 id="about-heading">About</h2>
          <p>
            Random Acts of Science. In October 2026 the Association for Human Mathematics said of a 700-proof drop that{" "}
            <a href={statementUrl} rel="noreferrer">
              &ldquo;mathematicians did not ask for this work to be done.&rdquo;
            </a>{" "}
            Fair. Nobody asked for this either. We find science stuck on compute, run it, and hand the result to whoever was
            stuck &mdash; one report at a time, free, with the method attached. If that is useful to you, the{" "}
            {tipJarUrl ? <a href={tipJarUrl} rel="noreferrer">tip jar</a> : <span>tip jar <small>(link to come)</small></span>}{" "}
            funds more GPUs.
          </p>
        </section>
      </section>

      {owner ? (
        <div className={styles.banner2} role="status">
          <strong>Owner view.</strong> Nothing on this page has been sent to anyone. {pending} act{pending === 1 ? "" : "s"} waiting for
          your decision. Decisions are saved to <code>acts/decisions.json</code> and picked up by the scheduler.
        </div>
      ) : null}
      {error ? <div className={styles.error} role="alert">{error}</div> : null}

      <section className={styles.stats} aria-label="Totals">
        <div><b>{doc.stats.acts_done}</b><span>acts done</span></div>
        <div><b>{doc.stats.gpu_hours.toFixed(1)}</b><span>GPU-hours</span></div>
        <div><b>{doc.stats.approvals}</b><span>approvals</span></div>
        <div><b>{doc.stats.replies}</b><span>replies</span></div>
        {owner && <div><b>{doc.stats.queued}</b><span>queued</span></div>}
      </section>

      <div className={styles.layout}>
        <div>
          <h2 className={styles.sectionTitle}>Acts, newest first</h2>
          {doc.acts.length === 0 ? (
            <p className={styles.empty}>The first write-ups will appear here once their owners have approved them.</p>
          ) : (
            doc.acts.map((act) => <ActCard key={act.id} act={act} owner={owner} onDecide={decide} busy={busy} />)
          )}
        </div>

        {owner && (
          <aside className={styles.queue} aria-label="Candidate queue">
            <h2 className={styles.sectionTitle}>Next up ({doc.queue?.length ?? 0})</h2>
            {(doc.queue ?? []).map((q) => (
              <div key={q.slug} className={styles.qItem}>
                <a href={q.issue_url} rel="noreferrer">{q.repo}</a>
                <span className={styles.fine}> · {q.licence}{q.stars != null ? ` · ${q.stars} stars` : ""}{q.vram_gb ? ` · ~${q.vram_gb} GB VRAM` : ""}</span>
                <blockquote>{q.evidence_quote}</blockquote>
                {q.data_terms ? <p className={styles.fine}>Data: {q.data_terms}</p> : null}
              </div>
            ))}
            {doc.skipped?.length ? (
              <details>
                <summary>Gated out ({doc.skipped.length})</summary>
                {doc.skipped.map((s) => (
                  <p key={s.slug} className={styles.fine}><b>{s.repo}</b> ({s.licence || "no licence"}): {s.reason}</p>
                ))}
              </details>
            ) : null}
          </aside>
        )}
      </div>
      <p className={styles.fine}>Generated {doc.generated_at.slice(0, 16).replace("T", " ")} UTC from the scheduler&apos;s acts record.</p>
    </div>
  );
}
