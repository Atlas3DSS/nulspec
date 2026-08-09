import type { Metadata } from "next";
import Link from "next/link";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { getFableRefusalLedger } from "@/lib/fable-refusals";

export const dynamic = "force-static";

export const metadata: Metadata = {
  title: "Archived model-audit incident",
  description:
    "An archived NULSPEC operations incident preserving a Fable safeguard refusal, integration events, cost, and trace evidence.",
  alternates: {
    canonical: "/fable-refusals",
  },
  openGraph: {
    title: "Archived model-audit incident — NULSPEC",
    description:
      "Provider messages, integration events, costs, and hashes from a historical release-QA incident.",
    url: "/fable-refusals",
  },
  twitter: {
    title: "Archived model-audit incident — NULSPEC",
    description:
      "Provider messages, integration events, costs, and hashes from a historical release-QA incident.",
  },
};

const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 6,
});

const integer = new Intl.NumberFormat("en-US");

export default function FableRefusalsPage() {
  const ledger = getFableRefusalLedger();

  return (
    <>
      <SiteHeader />
      <main id="main-content" className="refusal-page">
        <section className="refusal-hero">
          <div className="shell refusal-hero__grid">
            <div>
              <p className="hero__eyebrow">Operations archive · provider incident</p>
              <h1>Model-audit refusal, 2026-08-01</h1>
              <p className="refusal-hero__lede">
                This archived operations record preserves a case in which
                Anthropic&apos;s Fable model refused a release-consistency request
                before evaluating it. Provider output, costs, hashes, NULSPEC
                integration errors, and recovery attempts remain available for
                process audit. None of them carry scientific decision weight.
              </p>
              <Link className="refusal-hero__backlink" href="/operations">
                ← Operations ledger
              </Link>
            </div>
            <dl className="refusal-summary" aria-label="Refusal ledger summary">
              <div>
                <dt>Refusals</dt>
                <dd>{ledger.summary.refusal_count}</dd>
              </div>
              <div>
                <dt>Audit findings</dt>
                <dd>{ledger.summary.substantive_review_count}</dd>
              </div>
              <div>
                <dt>Charged</dt>
                <dd>{money.format(ledger.summary.total_charged_usd)}</dd>
              </div>
              <div>
                <dt>Studies delayed</dt>
                <dd>{ledger.summary.studies_delayed}</dd>
              </div>
            </dl>
          </div>
        </section>

        <section className="refusal-impact">
          <div className="shell refusal-impact__grid">
            <p className="section-kicker">Recorded consequence</p>
            <div>
              <h2>A paid audit returned no substantive output.</h2>
              <p>
                NULSPEC submitted a complete release packet. The invocation cost
                {" "}{money.format(ledger.summary.total_charged_usd)}, returned zero
                substantive findings, left the publication gate blocked, and
                duplicated operational checking before human disposition.
              </p>
              <p>
                This record describes the observed process outcome, not provider
                intent and not the validity of the replicated paper. The policy was
                superseded; the event is retained so future release systems can be
                tested against the same failure mode.
              </p>
            </div>
          </div>
        </section>

        <section className="refusal-ledger shell" aria-labelledby="ledger-heading">
          <div className="section-heading refusal-ledger__heading">
            <p className="section-kicker">Append-only evidence</p>
            <div>
              <h2 id="ledger-heading">Recorded provider event</h2>
              <p>
                Entries are never deleted. Corrections are appended, and every
                original trace remains bound by SHA-256.
              </p>
            </div>
          </div>

          {ledger.refusals.map((entry) => (
            <article className="refusal-record" key={entry.id} data-refusal-id={entry.id}>
              <header className="refusal-record__header">
                <div>
                  <p className="refusal-record__id">{entry.id}</p>
                  <h3>{entry.product}: {entry.refusal.category} safeguard refusal</h3>
                  <p>
                    {new Date(entry.occurred_at_utc).toLocaleString("en-US", {
                      dateStyle: "long",
                      timeStyle: "long",
                      timeZone: "UTC",
                    })} UTC
                  </p>
                </div>
                <span className="refusal-record__state">No review returned</span>
              </header>

              <div className="refusal-record__study">
                <div>
                  <span>Study</span>
                  <strong>{entry.study.title}</strong>
                </div>
                <a href={entry.study.arxiv_url}>arXiv {entry.study.arxiv_id} ↗</a>
              </div>

              <div className="refusal-record__metrics">
                <dl>
                  <div>
                    <dt>Anthropic charge</dt>
                    <dd>{money.format(entry.usage.total_charged_usd)}</dd>
                  </div>
                  <div>
                    <dt>Submitted packet</dt>
                    <dd>{integer.format(entry.request.packet_byte_count)} bytes</dd>
                  </div>
                  <div>
                    <dt>Cache input</dt>
                    <dd>{integer.format(entry.usage.fable_cache_creation_input_tokens)} tokens</dd>
                  </div>
                  <div>
                    <dt>Findings returned</dt>
                    <dd>{entry.refusal.substantive_findings_returned}</dd>
                  </div>
                </dl>
              </div>

              <div className="refusal-record__body">
                <section aria-labelledby={`${entry.id}-response`}>
                  <p className="section-kicker">Provider response</p>
                  <h3 id={`${entry.id}-response`}>Anthropic&apos;s recorded message</h3>
                  <blockquote>{entry.refusal.provider_message}</blockquote>
                  <p className="refusal-record__instruction">
                    The wrapper separately instructed API integrators to
                    configure a fallback model. Fable did not evaluate the
                    replication or return any scientific finding. This is a
                    charged operational non-response with decision weight
                    {" "}{entry.refusal.decision_weight}, not a scientific
                    {" "}<code>HARD_FAIL</code>.
                  </p>
                </section>

                <section aria-labelledby={`${entry.id}-impact`}>
                  <p className="section-kicker">Cost and process impact</p>
                  <h3 id={`${entry.id}-impact`}>Observed cost and duplicated work</h3>
                  <p>{entry.impact.explanation}</p>
                  <dl className="refusal-cost-breakdown">
                    <div>
                      <dt>Fable</dt>
                      <dd>{money.format(entry.usage.fable_charged_usd)}</dd>
                    </div>
                    <div>
                      <dt>Support model</dt>
                      <dd>{money.format(entry.usage.support_model_charged_usd)}</dd>
                    </div>
                    <div>
                      <dt>Publication state</dt>
                      <dd>{entry.impact.publication_gate}</dd>
                    </div>
                  </dl>
                </section>
              </div>

              <section className="supplemental-review" aria-labelledby={`${entry.id}-supplemental`}>
                <div className="supplemental-review__heading">
                  <div>
                    <p className="section-kicker">Supplemental automated QA</p>
                    <h3 id={`${entry.id}-supplemental`}>
                      GLM and Kimi returned contract-valid audit outputs.
                    </h3>
                  </div>
                  <strong>
                    {ledger.summary.fallback_valid_review_count} valid / {" "}
                    {ledger.summary.fallback_distinct_valid_model_count} models
                  </strong>
                </div>
                <p className="supplemental-review__comparison">
                  Four valid outputs across two model families returned eight-area {" "}
                  <strong>PASS</strong> checks on the release packet. These outputs
                  are automated consistency audits, not peer review, domain expertise,
                  or independent replications. The depth comparison preserves three
                  parameter variants for operations analysis. For cost accounting,
                  the refused invocation cost {" "}
                  {entry.supplemental_reviews.anthropic_to_high_depth_glm_cost_ratio} times
                  the high-depth GLM audit and {" "}
                  {entry.supplemental_reviews.anthropic_to_high_depth_kimi_cost_ratio} times
                  the high-depth Kimi audit.
                </p>
                {entry.supplemental_reviews.comparison_sets.map((comparison) => (
                  <section
                    className="review-depth-comparison"
                    data-comparison-group={comparison.comparison_group}
                    key={comparison.comparison_group}
                    aria-labelledby={`${comparison.comparison_group}-heading`}
                  >
                    <div className="review-depth-comparison__heading">
                      <div>
                        <p className="section-kicker">Saved comparison set</p>
                        <h4 id={`${comparison.comparison_group}-heading`}>
                          Audit depth comparison
                        </h4>
                      </div>
                      <a href={comparison.public_index_url}>Comparison JSON ↗</a>
                    </div>
                    <p>{comparison.purpose}</p>
                    <div className="review-depth-comparison__grid">
                      {comparison.attempt_ids.map((attemptId) => {
                        const attempt = entry.supplemental_reviews.attempts.find(
                          (candidate) => candidate.attempt_id === attemptId,
                        );
                        if (!attempt) return null;
                        return (
                          <article key={attempt.attempt_id}>
                            <div className="supplemental-review__attempt-head">
                              <span>{attempt.attempt_id}</span>
                              <strong>{attempt.model_id}</strong>
                            </div>
                            <dl>
                              <div>
                                <dt>Reasoning</dt>
                                <dd>
                                  {"reasoning_effort" in attempt
                                    ? attempt.reasoning_effort
                                    : "low"}
                                </dd>
                              </div>
                              <div>
                                <dt>Output limit</dt>
                                <dd>
                                  {"max_tokens" in attempt &&
                                  typeof attempt.max_tokens === "number"
                                    ? integer.format(attempt.max_tokens)
                                    : "32,768"}
                                </dd>
                              </div>
                              <div>
                                <dt>Actual output</dt>
                                <dd>{integer.format(attempt.completion_tokens)} tokens</dd>
                              </div>
                              <div>
                                <dt>Reasoning used</dt>
                                <dd>
                                  {integer.format(
                                    "reasoning_tokens" in attempt &&
                                      typeof attempt.reasoning_tokens === "number"
                                      ? attempt.reasoning_tokens
                                      : 0,
                                  )} tokens
                                </dd>
                              </div>
                              <div>
                                <dt>Elapsed</dt>
                                <dd>
                                  {"elapsed_seconds" in attempt &&
                                  typeof attempt.elapsed_seconds === "number"
                                    ? `${attempt.elapsed_seconds.toFixed(1)} s`
                                    : "not recorded"}
                                </dd>
                              </div>
                              <div>
                                <dt>Charge</dt>
                                <dd>{money.format(attempt.charged_usd)}</dd>
                              </div>
                            </dl>
                            {"public_result_url" in attempt ? (
                              <a href={attempt.public_result_url}>Validated audit JSON ↗</a>
                            ) : null}
                          </article>
                        );
                      })}
                    </div>
                  </section>
                ))}

                <details className="supplemental-review__history">
                  <summary>
                    Complete paid-attempt history ({entry.supplemental_reviews.attempts.length})
                  </summary>
                  <div className="supplemental-review__attempts">
                    {entry.supplemental_reviews.attempts.map((attempt) => (
                      <article
                        className={
                          attempt.status === "completed_valid"
                            ? "supplemental-review__attempt supplemental-review__attempt--valid"
                            : "supplemental-review__attempt"
                        }
                        key={attempt.attempt_id}
                      >
                        <div className="supplemental-review__attempt-head">
                          <span>{attempt.attempt_id}</span>
                          <strong>{attempt.model_id}</strong>
                        </div>
                        <dl>
                          <div>
                            <dt>Status</dt>
                            <dd>{attempt.status.replaceAll("_", " ")}</dd>
                          </div>
                          <div>
                            <dt>Indicated verdict</dt>
                            <dd>{attempt.indicated_verdict}</dd>
                          </div>
                          <div>
                            <dt>Charge</dt>
                            <dd>{money.format(attempt.charged_usd)}</dd>
                          </div>
                          <div>
                            <dt>Tokens</dt>
                            <dd>
                              {integer.format(attempt.prompt_tokens)} in / {" "}
                              {integer.format(attempt.completion_tokens)} out
                            </dd>
                          </div>
                        </dl>
                        <p>{attempt.finding}</p>
                        {"public_result_url" in attempt ? (
                          <a href={attempt.public_result_url}>Validated audit JSON ↗</a>
                        ) : null}
                      </article>
                    ))}
                  </div>
                </details>

                <details className="supplemental-review__history">
                  <summary>
                    No-charge transport and integration events ({ledger.summary.fallback_transport_event_count})
                  </summary>
                  <div className="supplemental-review__transport">
                    {entry.supplemental_reviews.transport_records.map((record) => (
                      <article key={record.event_id}>
                        <strong>{record.event_id}: {record.status.replaceAll("_", " ")}</strong>
                        <p>{record.responsibility}</p>
                        <p>{record.resolution}</p>
                      </article>
                    ))}
                  </div>
                </details>
              </section>

              <details className="refusal-evidence">
                <summary>Trace integrity and public projection</summary>
                <dl>
                  <div>
                    <dt>Reviewed commit</dt>
                    <dd><code>{entry.request.reviewed_commit}</code></dd>
                  </div>
                  <div>
                    <dt>Packet SHA-256</dt>
                    <dd><code>{entry.request.packet_sha256}</code></dd>
                  </div>
                  <div>
                    <dt>Prompt SHA-256</dt>
                    <dd><code>{entry.request.prompt_sha256}</code></dd>
                  </div>
                  <div>
                    <dt>Raw response SHA-256</dt>
                    <dd><code>{entry.evidence.raw_response_sha256}</code></dd>
                  </div>
                  <div>
                    <dt>Raw response bytes</dt>
                    <dd>{integer.format(entry.evidence.raw_response_byte_count)}</dd>
                  </div>
                  <div>
                    <dt>Standard error</dt>
                    <dd>{entry.evidence.stderr_byte_count} bytes</dd>
                  </div>
                </dl>
                <p>{entry.evidence.public_projection}</p>
                <div className="refusal-evidence__links">
                  <a href={entry.evidence.structured_result_url}>Structured result ↗</a>
                  <a href={entry.evidence.human_record_url}>Human-readable record ↗</a>
                </div>
              </details>
            </article>
          ))}
        </section>

        <section className="refusal-principle">
          <div className="shell refusal-impact__grid">
            <p className="section-kicker">Accountability standard</p>
            <div>
              <h2>Failures stay in the record.</h2>
              <p>
                NULSPEC publishes its own authentication, prompting, schema, and
                routing mistakes alongside external service failures. Each event
                is attributed to the narrowest supported cause, corrected by an
                appended record, and never converted into a scientific verdict.
              </p>
              <p>
                An operational incident is useful when it prevents recurrence.
                Keeping it separate from the scientific program prevents a provider
                dispute from being mistaken for research evidence.
              </p>
            </div>
          </div>
        </section>

        <section className="refusal-fallback">
          <div className="shell refusal-fallback__grid">
            <div>
              <p className="section-kicker">Current release-QA policy</p>
              <h2>Per-paper packet checks use GLM and Kimi.</h2>
            </div>
            <div>
              <p>
                GLM and Kimi receive the same immutable release packet and run
                separate automated consistency audits. Both must return a valid PASS
                to satisfy the QA gate; missing, malformed, non-PASS, or disagreeing
                outputs remain blocked for human inspection. These model outputs have
                zero scientific weight. Publication and email each require a separate
                human decision.
              </p>
              <p>
                Fable is not used for per-paper audit, release, repair, fallback,
                or escalation. After ten completed pipelines validate, one Fable
                call checks a reproducible random sample of three as a zero-weight
                process audit. It cannot change a paper result or authorize
                publication or email.
              </p>
              <ul>
                {ledger.review_policy.reviewers.map((reviewer) => (
                  <li key={reviewer.reviewer_family}>
                    <strong>{reviewer.reviewer_family}</strong>
                    <code>{reviewer.model_id}</code>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
