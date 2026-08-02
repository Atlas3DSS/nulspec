import { AccuracyRunLedger } from "@/components/accuracy-run-ledger";
import { AccuracyVarianceChart } from "@/components/accuracy-variance-chart";
import { ExtensionVoteForm } from "@/components/extension-vote-form";
import { HorizontalScrollRegion } from "@/components/horizontal-scroll-region";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { StatusStrip } from "@/components/status-strip";
import { StudyStateRail } from "@/components/study-state-rail";
import {
  GITHUB_URL,
  KOFI_URL,
  NOMINATE_URL,
  artifactUrl,
  formatAsOf,
  protocolUrl,
  type AccuracyPointDifference,
  type AccuracyStudyDocument,
  type ExtensionCallToAction,
  type PublicationArtifact,
} from "@/lib/study";

const artifactLabels: Record<string, string> = {
  result_summary: "One-page result",
  full_report: "Full report",
  machine_analysis: "Primary machine analysis",
  primary_figure: "Primary accuracy figure",
  frozen_primary_protocol: "Frozen primary protocol",
  extension_roadmap: "Extension roadmap",
  frontend_handoff: "Typed frontend contract",
  upstream_audit: "Upstream implementation audit",
  posthoc_register: "Post-hoc diagnostic register",
  posthoc_loss_contract: "Post-hoc loss-contract result",
  executed_code_manifest: "Executed-code manifest",
  peer_review_protocol: "Final peer-review protocol",
  peer_review_result: "Final peer-review result",
  peer_review_summary: "Final peer-review summary",
  peer_review_action_closure: "Final peer-review action closure",
};

const extensionSummaries: Record<string, string> = {
  "author-intent":
    "Obtain the canonical implementation, complete arguments, seeds, checkpoint rule, loss inputs, ASR selection, and Hessian provenance before rerunning.",
  "clean-room":
    "Have an independent operator reproduce the public result using only the tagged container and acquisition instructions, while recording ambiguities.",
  "more-seeds":
    "Run at least ten prospectively fixed seeds for the released path, clarified author-intent path, and scratch control, without excluding collapses.",
  factorial:
    "Prospectively isolate supervised-loss input, initialization, and ASR checkpoint selection while holding the remaining optimizer behavior fixed.",
  curvature:
    "Freeze common data, loss input, probes, estimator tolerance, and checkpoint selection, then report raw curvature probes with uncertainty.",
  "modern-baselines":
    "After reconciling the malaria method, compare current distillation baselines across additional datasets, architectures, and seeds.",
};

const comparisonLabels = [
  {
    key: "sprkd_upstream_direct_init_minus_control_student",
    label: "Exact public SPRKD − Control-S",
  },
  {
    key: "sprkd_paper_random_init_minus_control_student",
    label: "Paper-intent SPRKD − Control-S",
  },
  {
    key: "sprkd_paper_random_init_minus_rkd_paper_weak_teacher",
    label: "Paper-intent SPRKD − response KD",
  },
] as const;

function accuracy(value: number) {
  return `${value.toFixed(3)}%`;
}

function signedPoints(value: number) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(3)} points`;
}

function interval(value: AccuracyPointDifference) {
  return `${signedPoints(value.t95_interval[0])} to ${signedPoints(value.t95_interval[1])}`;
}

function diagnosticScope(value: unknown) {
  if (
    value !== null &&
    typeof value === "object" &&
    "scope" in value &&
    typeof value.scope === "string"
  ) {
    return value.scope;
  }
  return "See the linked diagnostic record for its registered scope.";
}

function ArtifactLink({ artifact }: { artifact: PublicationArtifact }) {
  return (
    <a className="result-artifact" href={artifactUrl(artifact)}>
      <span>{artifactLabels[artifact.role] ?? artifact.role.replaceAll("_", " ")}</span>
      <code>{artifact.sha256.slice(0, 12)}</code>
      <span aria-hidden="true">↗</span>
    </a>
  );
}

function extensionCallToAction(
  study: AccuracyStudyDocument,
): ExtensionCallToAction {
  return {
    requested: true,
    implementation_owner: "website_team",
    button_label: study.extension_vote.button_label,
    prompt: study.extension_vote.question,
    selection_mode: "single_choice",
    options: study.extension_vote.choices.map((choice, index) => ({
      ...choice,
      priority: index + 1,
      summary:
        extensionSummaries[choice.id] ??
        "Schedule this option under a new prospective protocol.",
    })),
  };
}

function hardwareProfiles(study: AccuracyStudyDocument) {
  const profiles = new Map<
    string,
    { gpu: string; cuda: string; torch: string; python: string; memory: number }
  >();
  for (const run of study.arms) {
    const key = [
      run.environment.gpu.name,
      run.environment.cuda_runtime,
      run.environment.torch,
      run.environment.python,
    ].join("|");
    profiles.set(key, {
      gpu: run.environment.gpu.name,
      cuda: run.environment.cuda_runtime,
      torch: run.environment.torch,
      python: run.environment.python.split(" ")[0],
      memory: run.environment.gpu.total_memory_bytes,
    });
  }
  return [...profiles.values()];
}

function peerReviewStatus(study: AccuracyStudyDocument) {
  if (study.final_peer_review.status === "approved") {
    return "Publication authorized by the one-shot final review";
  }
  if (study.final_peer_review.status === "approved_after_three_action_closure") {
    return "Publication authorized after the exact three-action closure";
  }
  return "Publication authorized after recorded human disposition";
}

export function AccuracyStudyRecord({
  study,
}: {
  study: AccuracyStudyDocument;
}) {
  const exact = study.primary.metrics.exact_public_sprkd.observed;
  const intent = study.primary.metrics.paper_intent_sprkd.observed;
  const responseKd = study.primary.metrics.paper_intent_response_kd.observed;
  const lossContract = study.diagnostics.posthoc_loss_contract;
  const correctedSprkd = lossContract.models.sprkd_logit_ce_random_init?.accuracy;
  const correctedControl = lossContract.models.control_student_logit_ce?.accuracy;
  const profiles = hardwareProfiles(study);
  const machineArtifact = study.artifacts.find(
    (artifact) => artifact.role === "machine_analysis",
  );
  const figureArtifact = study.artifacts.find(
    (artifact) => artifact.role === "primary_figure",
  );

  return (
    <>
      <SiteHeader />
      <StatusStrip study={study} />
      <main id="main-content" className="study-page accuracy-study-page">
        <header className="study-hero">
          <div className="shell">
            <div className="study-hero__meta">
              <span>STUDY {study.study_id}</span>
              <span>REPORTED {formatAsOf(study.as_of_utc).toUpperCase()} UTC</span>
            </div>
            <p className="hero__eyebrow">
              <span className="live-dot live-dot--steady" aria-hidden="true" />
              {study.state}
            </p>
            <h1>{study.study.title}</h1>
            <p className="study-hero__citation">
              arXiv:{study.study.arxiv_id} · evidence revision{" "}
              <code>{study.source.evidence_revision.slice(0, 12)}</code>
            </p>
            <div className="plain-link-row">
              <a href={study.study.arxiv_url}>Original paper ↗</a>
              <a href={protocolUrl(study)}>Frozen protocol ↗</a>
              <a href={GITHUB_URL}>Public record ↗</a>
            </div>
            <StudyStateRail current={study.state} />
          </div>
        </header>

        <section className="study-section accuracy-outcome-section">
          <div className="shell study-section__grid">
            <div className="study-section__number">01</div>
            <div className="study-section__body">
              <p className="section-kicker">Frozen result</p>
              <h2>Replication outcome and method assessment</h2>
              <div className="accuracy-outcome-grid">
                <article>
                  <span>Replication outcome</span>
                  <strong>Not replicated</strong>
                  <p>
                    The public five-seed final result did not reproduce the reported
                    stable accuracy and ordering.
                  </p>
                </article>
                <article>
                  <span>Underlying method</span>
                  <strong>Inconclusive</strong>
                  <p>
                    Missing historical implementation and checkpoint-selection
                    provenance prevent a method-level conclusion.
                  </p>
                </article>
              </div>
              <p className="study-section__lead">{study.classification.rationale}</p>
              <p className="study-note">
                “Not replicated” describes this preregistered public rerun. It does not
                mean that the underlying method has been disproved.
              </p>
            </div>
          </div>
        </section>

        <section className="study-section study-section--tinted">
          <div className="shell study-section__grid">
            <div className="study-section__number">02</div>
            <div className="study-section__body">
              <p className="section-kicker">Registered scope</p>
              <h2>{study.study.scope}</h2>
              <p className="study-section__lead">
                We tested the paper&apos;s reported 94.80% SPRKD result and its ordering
                against Control-S and response KD using five frozen training seeds.
              </p>
              <dl className="digest-list accuracy-contract-list">
                <div>
                  <dt>Primary estimator</dt>
                  <dd>Final sample-weighted validation accuracy</dd>
                </div>
                <div>
                  <dt>Independent units</dt>
                  <dd>Five training seeds</dd>
                </div>
                <div>
                  <dt>Uncertainty</dt>
                  <dd>Descriptive Student t interval across seeds</dd>
                </div>
                <div>
                  <dt>Decision source</dt>
                  <dd><code>{study.classification.decision_source}</code></dd>
                </div>
              </dl>
              <p className="study-note">
                The intervals summarize fresh-training variability over the frozen
                seeds. They are not prompt bootstrap intervals and do not establish
                practical equivalence.
              </p>
            </div>
          </div>
        </section>

        <section className="study-section accuracy-variance-section">
          <div className="shell study-section__grid">
            <div className="study-section__number">03</div>
            <div className="study-section__body">
              <AccuracyVarianceChart study={study} />
              <div className="accuracy-summary-grid">
                <article>
                  <span>Exact public SPRKD</span>
                  <strong>{accuracy(exact.mean)}</strong>
                  <small>SD {accuracy(exact.sample_sd)} · paper {accuracy(study.paper_reported_accuracy.sprkd)}</small>
                </article>
                <article>
                  <span>Paper-intent SPRKD</span>
                  <strong>{accuracy(intent.mean)}</strong>
                  <small>SD {accuracy(intent.sample_sd)} · paper {accuracy(study.paper_reported_accuracy.sprkd)}</small>
                </article>
                <article>
                  <span>Paper-intent response KD</span>
                  <strong>{accuracy(responseKd.mean)}</strong>
                  <small>SD {accuracy(responseKd.sample_sd)} · paper {accuracy(study.paper_reported_accuracy.response_kd)}</small>
                </article>
              </div>
              <div className="plain-link-row accuracy-figure-links">
                {figureArtifact ? (
                  <a href={artifactUrl(figureArtifact)}>Open research figure ↗</a>
                ) : null}
                {machineArtifact ? (
                  <a href={artifactUrl(machineArtifact)}>Open primary machine analysis ↗</a>
                ) : null}
              </div>
            </div>
          </div>
        </section>

        <section className="study-section study-section--ledger">
          <div className="shell study-section__grid">
            <div className="study-section__number">04</div>
            <div className="study-section__body">
              <AccuracyRunLedger study={study} />
            </div>
          </div>
        </section>

        <section className="study-section">
          <div className="shell study-section__grid">
            <div className="study-section__number">05</div>
            <div className="study-section__body">
              <p className="section-kicker">Paired comparisons</p>
              <h2>Accuracy differences across the five seeds</h2>
              <div className="accuracy-comparison-grid">
                {comparisonLabels.map(({ key, label }) => {
                  const comparison = study.primary.comparisons[key];
                  if (!comparison) return null;
                  const difference = comparison.accuracy_point_difference;
                  return (
                    <article key={key}>
                      <span>{label}</span>
                      <strong>{signedPoints(difference.mean)}</strong>
                      <dl>
                        <div>
                          <dt>Seed SD</dt>
                          <dd>{difference.sample_sd.toFixed(3)} points</dd>
                        </div>
                        <div>
                          <dt>Descriptive t interval</dt>
                          <dd>{interval(difference)}</dd>
                        </div>
                      </dl>
                    </article>
                  );
                })}
              </div>
              <p className="study-note">
                These are paired point differences for matched seeds. Per-seed exact
                McNemar tests are available on each run page because all compared
                models use that seed&apos;s same validation split.
              </p>
            </div>
          </div>
        </section>

        <section className="study-section study-section--tinted accuracy-diagnostics">
          <div className="shell study-section__grid">
            <div className="study-section__number">06</div>
            <div className="study-section__body">
              <p className="section-kicker">Diagnostics</p>
              <h2>Registered extensions and post-hoc analyses</h2>
              <div className="diagnostic-scope-grid">
                <article>
                  <span>Preregistered extensions</span>
                  <p>{diagnosticScope(study.diagnostics.preregistered_extensions)}</p>
                </article>
                <article>
                  <span>Preregistered common-probe Hessian analysis</span>
                  <p>{diagnosticScope(study.diagnostics.common_probe_hessian)}</p>
                </article>
                <article>
                  <span>Post-hoc stability analysis</span>
                  <p>{study.diagnostics.posthoc_stability.scope}</p>
                </article>
              </div>

              <aside className="posthoc-callout" aria-labelledby="posthoc-loss-heading">
                <div>
                  <p className="section-kicker">Post-hoc diagnostic · not verdict-bearing</p>
                  <h3 id="posthoc-loss-heading">Supervised-loss input correction</h3>
                  <p>{lossContract.scope}</p>
                </div>
                <dl>
                  <div>
                    <dt>Corrected SPRKD final mean</dt>
                    <dd>{correctedSprkd ? accuracy(correctedSprkd.mean) : "See result"}</dd>
                  </div>
                  <div>
                    <dt>Corrected Control-S final mean</dt>
                    <dd>{correctedControl ? accuracy(correctedControl.mean) : "See result"}</dd>
                  </div>
                </dl>
                <p>
                  Correcting only the supervised-loss input produced stable SPRKD
                  finals, but the paired Control-S mean remained higher. This
                  outcome-motivated diagnostic cannot replace the frozen primary
                  result.
                </p>
              </aside>

              <aside
                className="release-governance"
                aria-labelledby="release-governance-heading"
              >
                <div className="release-governance__heading">
                  <p className="section-kicker">Release governance · not scientific evidence</p>
                  <h3 id="release-governance-heading">Final review and author-email state</h3>
                </div>
                <div className="release-governance__grid">
                  <article>
                    <span>Final peer review</span>
                    <strong>{peerReviewStatus(study)}</strong>
                    <p>
                      Reviewer: {study.final_peer_review.reviewer}. Exactly one review
                      invocation was permitted; resubmission is forbidden.
                    </p>
                  </article>
                  <article>
                    <span>Author email</span>
                    <strong>
                      {study.author_email.dispatch_authorized
                        ? "Human approval recorded for the exact draft"
                        : "Pending final human approval; dispatch closed"}
                    </strong>
                    <p>
                      Fable can make the draft eligible for approval but cannot
                      authorize or send it. Draft SHA-256{" "}
                      <code>{study.author_email.draft_sha256.slice(0, 12)}</code>.
                    </p>
                  </article>
                </div>
              </aside>
            </div>
          </div>
        </section>

        <section className="study-section">
          <div className="shell study-section__grid">
            <div className="study-section__number">07</div>
            <div className="study-section__body">
              <p className="section-kicker">Provenance and evidence</p>
              <h2>Observed execution profiles and public artifacts</h2>
              <HorizontalScrollRegion label="Scrollable execution-profile table">
                <table className="hardware-table accuracy-hardware-table">
                  <thead>
                    <tr>
                      <th scope="col">GPU</th>
                      <th scope="col">Memory</th>
                      <th scope="col">CUDA runtime</th>
                      <th scope="col">PyTorch</th>
                      <th scope="col">Python</th>
                    </tr>
                  </thead>
                  <tbody>
                    {profiles.map((profile) => (
                      <tr key={`${profile.gpu}-${profile.cuda}-${profile.torch}`}>
                        <th scope="row">{profile.gpu}</th>
                        <td>{(profile.memory / 1024 ** 3).toFixed(1)} GiB</td>
                        <td>{profile.cuda}</td>
                        <td>{profile.torch}</td>
                        <td>{profile.python}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </HorizontalScrollRegion>
              <p className="study-note">
                Total recorded device-process time was{" "}
                {study.compute.recorded_device_process_hours_total.toFixed(2)} hours.
                This is process accounting, not elapsed time or measured GPU-active
                time. Public records exclude device UUIDs, private paths, hostnames,
                service identifiers, addresses, and credentials.
              </p>
              <div className="result-artifacts" aria-label="Published study artifacts">
                {study.artifacts.map((artifact) => (
                  <ArtifactLink artifact={artifact} key={artifact.role} />
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="study-section extension-section">
          <div className="shell study-section__grid">
            <div className="study-section__number">08</div>
            <div className="study-section__body">
              <p className="section-kicker">Prospective follow-up</p>
              <h2>Choose the next evidence package</h2>
              <p className="study-section__lead">
                A vote helps prioritize a new prospectively registered study. It cannot
                alter this study&apos;s frozen not-replicated result.
              </p>
              <ExtensionVoteForm
                callToAction={extensionCallToAction(study)}
                studyId={study.study_id}
              />
            </div>
          </div>
        </section>

        <section className="study-cta">
          <div className="shell study-cta__grid">
            <div>
              <p className="section-kicker">Continue the work</p>
              <h2>Nominate or support another replication</h2>
            </div>
            <div className="button-row">
              <a className="button button--primary" href={NOMINATE_URL}>Nominate a paper</a>
              <a className="button button--secondary" href={KOFI_URL}>Support NULSPEC</a>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
