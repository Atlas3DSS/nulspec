import type { Metadata } from "next";
import Link from "next/link";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { StatusStrip } from "@/components/status-strip";
import { getSelectionLedger, type SelectionCandidate } from "@/lib/selection-ledger";
import { getLatestStudy } from "@/lib/study";

export const dynamic = "force-static";

export const metadata: Metadata = {
  title: "Selection ledger",
  description:
    "Every paper NULSPEC has considered, including selection status, exclusion reasons, feasibility, resource estimates, and final-cost state.",
  alternates: { canonical: "/selection" },
  openGraph: {
    title: "Paper selection ledger — NULSPEC",
    description:
      "The public denominator behind NULSPEC replication selection: considered, selected, deferred, rejected, and completed papers.",
    url: "/selection",
  },
};

const decisionLabels: Record<SelectionCandidate["decision"], string> = {
  completed: "Completed",
  selected: "Selected",
  deferred: "Deferred",
  rejected: "Rejected",
};

const costLabels: Record<SelectionCandidate["actual_cost"]["status"], string> = {
  audit_pending: "Final audit pending",
  in_progress: "In progress — not final",
  not_started: "Not started",
  final: "Final",
};

const number = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });
const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

function finalCost(candidate: SelectionCandidate) {
  const cost = candidate.actual_cost;
  if (
    cost.status !== "final" ||
    cost.gpu_hours === null ||
    cost.human_hours === null ||
    cost.direct_cost_usd === null
  ) {
    return costLabels[cost.status];
  }
  return `${number.format(cost.gpu_hours)} GPU-h · ${number.format(cost.human_hours)} human-h · ${money.format(cost.direct_cost_usd)}`;
}

export default function SelectionLedgerPage() {
  const study = getLatestStudy();
  const ledger = getSelectionLedger();

  return (
    <>
      <SiteHeader />
      <StatusStrip study={study} />
      <main id="main-content" className="selection-page">
        <section className="selection-hero">
          <div className="shell selection-hero__grid">
            <div>
              <p className="hero__eyebrow">Public selection denominator</p>
              <h1>Every paper considered, not only the papers run.</h1>
              <p className="selection-hero__lede">
                This append-only snapshot records selection reasons, deferrals,
                exclusions, estimated GPU and human effort, exact-versus-compatible
                feasibility, process state, and actual final cost when audited.
              </p>
              <div className="button-row">
                <Link className="button button--primary" href="/methodology">
                  Read selection rules
                </Link>
                <a className="button button--secondary" href="/data/selection-ledger.json">
                  Download JSON
                </a>
              </div>
            </div>
            <dl className="selection-summary">
              <div>
                <dt>Considered</dt>
                <dd>{ledger.summary.considered}</dd>
              </div>
              <div>
                <dt>Selected or complete</dt>
                <dd>{ledger.summary.selected + ledger.summary.completed}</dd>
              </div>
              <div>
                <dt>Deferred / rejected</dt>
                <dd>{ledger.summary.deferred} / {ledger.summary.rejected}</dd>
              </div>
              <div>
                <dt>NULSPEC 20</dt>
                <dd>{ledger.summary.quota_counted} / {ledger.summary.quota_target}</dd>
              </div>
            </dl>
          </div>
        </section>

        <section className="policy-notice">
          <div className="shell">
            <strong>Selection provenance:</strong>{" "}
            all records below predate methodology v{ledger.methodology_version} and
            are labeled <code>pre-policy-convenience-v1</code>. They are transparent,
            but they are not a randomized sample of ML papers.
          </div>
        </section>

        <section className="selection-ledger shell" aria-labelledby="selection-ledger-heading">
          <div className="selection-ledger__heading">
            <div>
              <p className="section-kicker">Snapshot</p>
              <h2 id="selection-ledger-heading">Candidate decisions</h2>
            </div>
            <p>
              As of {new Date(ledger.as_of_utc).toLocaleString("en-US", {
                dateStyle: "medium",
                timeStyle: "short",
                timeZone: "UTC",
              })} UTC. Null cost fields mean “not audited,” never zero.
            </p>
          </div>

          <ol className="selection-list">
            {ledger.candidates.map((candidate, index) => {
              const gates = [
                ["Protocol frozen", candidate.process.protocol_frozen],
                ["Terminal artifact", candidate.process.terminal_artifact_valid],
                ["Automated QA", candidate.process.automated_consistency_audit_complete],
                ["Human approval", candidate.process.human_publication_approved],
                ["Published", candidate.process.published],
              ] as const;

              return (
                <li
                  className={`selection-record selection-record--${candidate.decision}`}
                  data-paper-id={candidate.paper_id}
                  key={candidate.paper_id}
                >
                  <article>
                    <header className="selection-record__header">
                      <div>
                        <p>
                          <span>{String(index + 1).padStart(3, "0")}</span>
                          <code>{candidate.paper_id}</code>
                        </p>
                        <h2><a href={candidate.url}>{candidate.title}</a></h2>
                      </div>
                      <span className="selection-record__status">
                        {decisionLabels[candidate.decision]}
                      </span>
                    </header>

                    <div className="selection-record__claims">
                      <h3>Claim scope</h3>
                      <ul>
                        {candidate.claim_scope.map((claim) => <li key={claim}>{claim}</li>)}
                      </ul>
                    </div>

                    <div className="selection-record__decision-grid">
                      <section>
                        <h3>Why considered or selected</h3>
                        <ul>
                          {candidate.why_selected.map((reason) => <li key={reason}>{reason}</li>)}
                        </ul>
                      </section>
                      <section>
                        <h3>Why deferred or rejected</h3>
                        {candidate.why_not_started_or_rejected.length > 0 ? (
                          <ul>
                            {candidate.why_not_started_or_rejected.map((reason) => (
                              <li key={reason}>{reason}</li>
                            ))}
                          </ul>
                        ) : <p>Not applicable.</p>}
                      </section>
                    </div>

                    <dl className="selection-record__resources">
                      <div>
                        <dt>Estimated GPU-hours</dt>
                        <dd>
                          {candidate.estimate.gpu_hours.min} min · {candidate.estimate.gpu_hours.likely} likely · {candidate.estimate.gpu_hours.max} max
                        </dd>
                      </div>
                      <div>
                        <dt>Estimated human-hours</dt>
                        <dd>{candidate.estimate.human_hours}</dd>
                      </div>
                      <div>
                        <dt>Feasibility</dt>
                        <dd>
                          <strong>{candidate.estimate.feasibility.class}</strong>{" "}
                          {candidate.estimate.feasibility.explanation}
                        </dd>
                      </div>
                      <div>
                        <dt>Actual final cost</dt>
                        <dd><strong>{finalCost(candidate)}</strong> {candidate.actual_cost.note}</dd>
                      </div>
                    </dl>

                    <footer className="selection-record__footer">
                      <div className="selection-record__gates" aria-label="Process gates">
                        {gates.map(([label, complete]) => (
                          <span className={complete ? "is-complete" : ""} key={label}>
                            {complete ? "✓" : "○"} {label}
                          </span>
                        ))}
                      </div>
                      <p>
                        <span>Selection method</span>
                        Priority-selected before randomized policy · {candidate.process.quota_counted ? "counts toward NULSPEC 20" : "does not yet count"}
                      </p>
                    </footer>
                  </article>
                </li>
              );
            })}
          </ol>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
