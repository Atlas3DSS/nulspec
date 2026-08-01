import { ArmEvidenceTabs } from "@/components/arm-evidence-tabs";
import { HorizontalScrollRegion } from "@/components/horizontal-scroll-region";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { StatusStrip } from "@/components/status-strip";
import {
  armEvidenceUrl,
  artifactUrl,
  type AccuracyRunComparison,
  type AccuracyStudyArm,
  type AccuracyStudyDocument,
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
};

const modelDefinitions = [
  {
    key: "exact_public_sprkd",
    label: "SPRKD · exact public path",
    paperKey: "sprkd",
    evidence: "Primary released-code path",
  },
  {
    key: "paper_intent_sprkd",
    label: "SPRKD · paper-intent path",
    paperKey: "sprkd",
    evidence: "Narrow paper-intent path",
  },
  {
    key: "control_student",
    label: "Control-S",
    paperKey: "control_student",
    evidence: "Shared scratch control",
  },
  {
    key: "paper_intent_response_kd",
    label: "Response KD · paper intent",
    paperKey: "response_kd",
    evidence: "Untouched weak-teacher path",
  },
  {
    key: "exact_public_response_kd",
    label: "Response KD · exact public path",
    paperKey: "response_kd",
    evidence: "ASR-mutated-teacher path",
  },
  {
    key: "control_teacher",
    label: "Control-T",
    paperKey: "control_teacher",
    evidence: "Teacher control",
  },
  {
    key: "weak_teacher",
    label: "Weak teacher",
    paperKey: "weak_teacher",
    evidence: "Unmodified ensemble mean",
  },
] as const;

const comparisonDefinitions = [
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

function elapsed(value: number | undefined) {
  if (value === undefined) return "Not applicable";
  return `${(value / 60).toFixed(1)} min`;
}

function pValue(value: number) {
  if (value === 0) return "0 (numeric underflow)";
  if (value < 0.0001) return value.toExponential(3);
  return value.toFixed(4);
}

function ArtifactCard({ artifact }: { artifact: PublicationArtifact }) {
  return (
    <a className="arm-artifact" href={artifactUrl(artifact)}>
      <span>{artifactLabels[artifact.role] ?? artifact.role.replaceAll("_", " ")}</span>
      <code>SHA-256 {artifact.sha256.slice(0, 12)}</code>
      <span aria-hidden="true">↗</span>
    </a>
  );
}

function McNemarCard({
  comparison,
  label,
}: {
  comparison: AccuracyRunComparison;
  label: string;
}) {
  const result = comparison.mcnemar_exact;
  return (
    <article className="mcnemar-card">
      <div className="mcnemar-card__heading">
        <span>{label}</span>
        <strong>{signedPoints(comparison.accuracy_point_difference)}</strong>
      </div>
      <dl className="mcnemar-cells">
        <div>
          <dt>Both correct</dt>
          <dd>{result.a_correct_b_correct.toLocaleString()}</dd>
        </div>
        <div>
          <dt>A correct, B wrong</dt>
          <dd>{result.a_correct_b_wrong.toLocaleString()}</dd>
        </div>
        <div>
          <dt>A wrong, B correct</dt>
          <dd>{result.a_wrong_b_correct.toLocaleString()}</dd>
        </div>
        <div>
          <dt>Both wrong</dt>
          <dd>{result.a_wrong_b_wrong.toLocaleString()}</dd>
        </div>
      </dl>
      <p>
        Exact McNemar p = <code>{pValue(result.p_value)}</code> · log10 p ={" "}
        <code>{result.log10_p_value.toFixed(3)}</code> · n = {result.n.toLocaleString()}
      </p>
    </article>
  );
}

function modelRows(arm: AccuracyStudyArm, study: AccuracyStudyDocument) {
  return modelDefinitions.flatMap((definition) => {
    const model = arm.models[definition.key];
    const finalAccuracy = arm.metrics[definition.key];
    if (!model || finalAccuracy === undefined) return [];
    return [
      {
        ...definition,
        model,
        finalAccuracy,
        paperAccuracy: study.paper_reported_accuracy[definition.paperKey],
      },
    ];
  });
}

function ResultBar({
  value,
  paper,
  label,
}: {
  value: number;
  paper: number;
  label: string;
}) {
  const minimum = 45;
  const position = (candidate: number) =>
    Math.min(100, Math.max(0, ((candidate - minimum) / (100 - minimum)) * 100));
  return (
    <div className="accuracy-result-bar">
      <span>{label}</span>
      <div
        aria-label={`${label}: seed accuracy ${accuracy(value)}; paper mean ${accuracy(paper)}.`}
        className="accuracy-result-bar__plot"
        role="img"
      >
        <i className="accuracy-result-bar__fill" style={{ width: `${position(value)}%` }} />
        <i className="accuracy-result-bar__paper" style={{ left: `${position(paper)}%` }} />
      </div>
      <strong>{accuracy(value)}</strong>
    </div>
  );
}

export function AccuracyRunRecord({
  arm,
  study,
}: {
  arm: AccuracyStudyArm;
  study: AccuracyStudyDocument;
}) {
  const armIndex = study.arms.findIndex((item) => item.arm_id === arm.arm_id);
  const previousArm = study.arms[armIndex - 1];
  const nextArm = study.arms[armIndex + 1];
  const rows = modelRows(arm, study);
  const selectedBars = rows.slice(0, 4);

  return (
    <>
      <SiteHeader />
      <StatusStrip study={study} />
      <main id="main-content" className="arm-page accuracy-arm-page">
        <header className="arm-hero">
          <div className="shell">
            <div className="arm-hero__meta">
              <span>STUDY {study.study_id}</span>
              <span>SEED {arm.seed} / 4</span>
            </div>
            <a className="arm-back-link" href={`/studies/${study.study_id}`}>
              ← Study record
            </a>
            <p className="section-kicker">Frozen primary trial</p>
            <h1>Seed {arm.seed} evidence</h1>
            <p className="arm-hero__configuration">
              <code>{arm.run_id}</code> · {arm.gpu}
            </p>
            <p className="arm-hero__summary">
              This page reports one of five independent training seeds using final
              sample-weighted validation accuracy. It provides single-seed evidence;
              the study classification is calculated from the complete five-seed
              result.
            </p>

            <div className="arm-outcome-grid accuracy-arm-outcomes">
              <div>
                <span>Run interpretation</span>
                <strong>Single-seed evidence</strong>
                <small>No per-seed replication verdict is assigned.</small>
              </div>
              <div>
                <span>Frozen study outcome</span>
                <strong className="arm-study-classification">Not replicated</strong>
                <small>Underlying method assessment: inconclusive.</small>
              </div>
            </div>
          </div>
        </header>

        <ArmEvidenceTabs>
          <section className="study-section arm-section" id="comparison">
            <div className="shell study-section__grid">
              <div className="study-section__number">01</div>
              <div className="study-section__body">
                <p className="section-kicker">Paper means and seed result</p>
                <h2>Final accuracy on the shared validation split</h2>
                <div className="accuracy-result-bars">
                  {selectedBars.map((row) => (
                    <ResultBar
                      key={row.key}
                      label={row.label}
                      paper={row.paperAccuracy}
                      value={row.finalAccuracy}
                    />
                  ))}
                </div>
                <p className="study-note">
                  Bars start at 45% to make chance-level collapses visible. The thin
                  marker is the corresponding paper-reported mean. It is a reference
                  value, not a single-seed acceptance threshold.
                </p>

                <HorizontalScrollRegion label="Scrollable seed model comparison table">
                  <table className="hardware-table accuracy-model-table">
                    <thead>
                      <tr>
                        <th scope="col">Model path</th>
                        <th scope="col">Paper mean</th>
                        <th scope="col">Seed final</th>
                        <th scope="col">Difference</th>
                        <th scope="col">Evidence role</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row) => (
                        <tr key={row.key}>
                          <th scope="row">{row.label}</th>
                          <td>{accuracy(row.paperAccuracy)}</td>
                          <td>{accuracy(row.finalAccuracy)}</td>
                          <td>{signedPoints(row.finalAccuracy - row.paperAccuracy)}</td>
                          <td>{row.evidence}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </HorizontalScrollRegion>

                <div className="mcnemar-grid">
                  {comparisonDefinitions.map(({ key, label }) => {
                    const comparison = arm.comparisons[key];
                    return comparison ? (
                      <McNemarCard comparison={comparison} key={key} label={label} />
                    ) : null;
                  })}
                </div>
                <p className="study-note">
                  Exact McNemar tests compare paired predictions on this seed&apos;s same
                  validation split. They do not estimate training-to-training
                  variability; the study-level descriptive t intervals use all five
                  frozen seeds.
                </p>
              </div>
            </div>
          </section>

          <section className="study-section study-section--tinted arm-section" id="execution">
            <div className="shell study-section__grid">
              <div className="study-section__number">02</div>
              <div className="study-section__body">
                <p className="section-kicker">Selected execution</p>
                <h2>Final metric and training-history diagnostics</h2>
                <dl className="arm-fact-list accuracy-run-facts">
                  <div>
                    <dt>Run status</dt>
                    <dd>Complete; integrity checks passed</dd>
                  </div>
                  <div>
                    <dt>Selection rule</dt>
                    <dd>Final checkpoint</dd>
                  </div>
                  <div>
                    <dt>Primary metric</dt>
                    <dd>Sample-weighted full-validation accuracy</dd>
                  </div>
                  <div>
                    <dt>Validation targets</dt>
                    <dd>{arm.integrity.n_validation_targets.toLocaleString()}</dd>
                  </div>
                  <div>
                    <dt>Training stages</dt>
                    <dd>{arm.integrity.stage_count}</dd>
                  </div>
                </dl>

                <HorizontalScrollRegion label="Scrollable final and best-epoch metric table">
                  <table className="hardware-table accuracy-history-table">
                    <thead>
                      <tr>
                        <th scope="col">Model path</th>
                        <th scope="col">Final accuracy</th>
                        <th scope="col">Best epoch accuracy</th>
                        <th scope="col">Final cross-entropy</th>
                        <th scope="col">Recorded stage time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row) => (
                        <tr key={row.key}>
                          <th scope="row">{row.label}</th>
                          <td>{accuracy(row.finalAccuracy)}</td>
                          <td>
                            {row.model.best_valid_accuracy_unweighted_batch_mean === undefined
                              ? "Not applicable"
                              : accuracy(row.model.best_valid_accuracy_unweighted_batch_mean)}
                          </td>
                          <td>{row.model.cross_entropy_sample_weighted.toFixed(4)}</td>
                          <td>{elapsed(row.model.elapsed_seconds)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </HorizontalScrollRegion>
                <p className="study-note">
                  Final sample-weighted accuracy is the preregistered primary value.
                  Best-epoch accuracy is a post-hoc stability diagnostic and uses the
                  recorded unweighted batch mean; it cannot replace the selected final
                  checkpoint.
                </p>
              </div>
            </div>
          </section>

          <section className="study-section arm-section" id="provenance">
            <div className="shell study-section__grid">
              <div className="study-section__number">03</div>
              <div className="study-section__body">
                <p className="section-kicker">Hardware, software, and integrity</p>
                <h2>Observed execution profile</h2>
                <dl className="arm-fact-list accuracy-provenance-list">
                  <div>
                    <dt>GPU</dt>
                    <dd>{arm.environment.gpu.name}</dd>
                  </div>
                  <div>
                    <dt>Compute capability</dt>
                    <dd>{arm.environment.gpu.compute_capability}</dd>
                  </div>
                  <div>
                    <dt>GPU memory</dt>
                    <dd>{(arm.environment.gpu.total_memory_bytes / 1024 ** 3).toFixed(1)} GiB</dd>
                  </div>
                  <div>
                    <dt>CUDA runtime</dt>
                    <dd>{arm.environment.cuda_runtime}</dd>
                  </div>
                  <div>
                    <dt>cuDNN</dt>
                    <dd>{arm.environment.cudnn}</dd>
                  </div>
                  <div>
                    <dt>PyTorch</dt>
                    <dd>{arm.environment.torch}</dd>
                  </div>
                  <div>
                    <dt>NumPy</dt>
                    <dd>{arm.environment.numpy}</dd>
                  </div>
                  <div>
                    <dt>Python</dt>
                    <dd>{arm.environment.python}</dd>
                  </div>
                  <div className="is-wide">
                    <dt>Platform</dt>
                    <dd><code>{arm.environment.platform}</code></dd>
                  </div>
                </dl>

                <div className="accuracy-digest-grid">
                  {[
                    ["Run completion", arm.integrity.complete_sha256],
                    ["Configuration", arm.integrity.config_sha256],
                    ["Predictions", arm.integrity.predictions_sha256],
                    ["Split indices", arm.integrity.split_indices_sha256],
                    ["Validation indices", arm.integrity.validation_indices_sha256],
                  ].map(([label, digest]) => (
                    <div key={label}>
                      <span>{label}</span>
                      <code>{digest}</code>
                    </div>
                  ))}
                </div>

                <details className="accuracy-checkpoint-digests">
                  <summary>Stage checkpoint SHA-256 values</summary>
                  <dl>
                    {Object.entries(arm.integrity.stage_checkpoint_sha256s).map(
                      ([stage, digest]) => (
                        <div key={stage}>
                          <dt>{stage.replaceAll("_", " ")}</dt>
                          <dd><code>{digest}</code></dd>
                        </div>
                      ),
                    )}
                  </dl>
                </details>
                <p className="study-note">
                  The public profile includes observed hardware and software labels.
                  It excludes physical GPU UUIDs, private paths, raw hostnames, service
                  identifiers, addresses, and credentials.
                </p>
              </div>
            </div>
          </section>

          <section className="study-section study-section--tinted arm-section" id="evidence">
            <div className="shell study-section__grid">
              <div className="study-section__number">04</div>
              <div className="study-section__body">
                <p className="section-kicker">Public evidence</p>
                <h2>Hash-bound study artifacts</h2>
                <p>
                  The run is joined to the primary machine analysis by seed and exact
                  run identifier <code>{arm.run_id}</code>. Published artifacts are a
                  validated subset of the files explicitly declared by the research
                  handoff.
                </p>
                <div className="arm-artifact-grid" aria-label="Public study artifacts">
                  {study.artifacts.map((artifact) => (
                    <ArtifactCard artifact={artifact} key={artifact.role} />
                  ))}
                </div>
              </div>
            </div>
          </section>

          <section className="study-section arm-section" id="limitations">
            <div className="shell study-section__grid">
              <div className="study-section__number">05</div>
              <div className="study-section__body">
                <p className="section-kicker">Interpretation limits</p>
                <h2>What this run can and cannot establish</h2>
                <ul className="arm-limit-list">
                  <li>This page contains one frozen training seed: {arm.seed}.</li>
                  <li>
                    A single seed is not independently judged against the paper&apos;s
                    five-trial mean and does not receive a reproduced/not-reproduced
                    label.
                  </li>
                  <li>
                    The study&apos;s descriptive Student t intervals estimate variability
                    across the five independent frozen training seeds. They are not
                    prompt uncertainty and are not practical-equivalence tests.
                  </li>
                  <li>
                    Best-epoch values and the supervised-loss correction are diagnostic
                    evidence. Neither can replace the preregistered final-checkpoint
                    result.
                  </li>
                  <li>
                    The frozen replication outcome is <strong>not replicated</strong>;
                    the underlying method assessment remains <strong>inconclusive</strong>.
                  </li>
                </ul>

                <nav className="arm-pagination" aria-label="Adjacent frozen-seed pages">
                  {previousArm ? (
                    <a href={armEvidenceUrl(study.study_id, previousArm.arm_id)}>
                      <span>← Previous seed</span>
                      <strong>Seed {previousArm.seed}</strong>
                    </a>
                  ) : (
                    <span />
                  )}
                  {nextArm ? (
                    <a href={armEvidenceUrl(study.study_id, nextArm.arm_id)}>
                      <span>Next seed →</span>
                      <strong>Seed {nextArm.seed}</strong>
                    </a>
                  ) : null}
                </nav>
              </div>
            </div>
          </section>
        </ArmEvidenceTabs>
      </main>
      <SiteFooter />
    </>
  );
}
