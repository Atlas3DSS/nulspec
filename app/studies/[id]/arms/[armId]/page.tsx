import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ArmEvidenceTabs } from "@/components/arm-evidence-tabs";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { StatusStrip } from "@/components/status-strip";
import {
  armEvidenceUrl,
  artifactUrl,
  classificationLabel,
  formatPValue,
  formatSigned,
  getStudies,
  getStudyArm,
  type PublicationArtifact,
  type StudyArm,
} from "@/lib/study";

type ArmPageProps = {
  params: Promise<{ id: string; armId: string }>;
};

const artifactLabels: Record<string, string> = {
  result_summary: "Result summary",
  full_report: "Full matrix report",
  machine_analysis: "Machine-readable analysis",
  extension_roadmap: "Extension roadmap",
  website_handoff: "Website handoff contract",
  frontend_handoff: "Arm evidence specification",
};

const executionLabels: Record<StudyArm["execution"], string> = {
  completed: "Completed",
  completed_with_recovery: "Completed with recovery",
  failed: "Failed",
  aborted: "Aborted",
  inconclusive_terminal: "Terminal, inconclusive",
};

const directionLabels: Record<
  StudyArm["metrics"]["directional_assessment"],
  string
> = {
  agrees: "Agrees with the published direction",
  disagrees: "Disagrees with the published direction",
  inconclusive_interval_includes_zero:
    "Inconclusive because the conditional interval includes zero",
};

function conditionalInterval([low, high]: [number, number]) {
  return "[" + formatSigned(low) + ", " + formatSigned(high) + "]";
}

function directionSummary(arm: StudyArm) {
  if (arm.metrics.directional_assessment === "agrees") {
    return "The release-protocol result agrees with the published direction.";
  }
  if (arm.metrics.directional_assessment === "disagrees") {
    return "The release-protocol result disagrees with the published direction.";
  }
  return "The conditional release interval includes zero, so the directional result is inconclusive.";
}

function profileDescription(arm: StudyArm) {
  return arm.provenance === "EXACT"
    ? "Paper-pinned training stack and claim evaluation."
    : "Documented compatibility training with exact-stack claim evaluation.";
}

function ArmIntervalPlot({ arm }: { arm: StudyArm }) {
  const rows = [
    {
      id: "release",
      label: "Release sampled",
      point: arm.metrics.release_reward_delta,
      interval: arm.metrics.release_prompt_bootstrap_95_ci,
    },
    {
      id: "paired",
      label: "Paired deterministic",
      point: arm.metrics.independent_paired_reward_delta,
      interval: arm.metrics.independent_paired_bootstrap_95_ci,
    },
  ] as const;
  const published = arm.metrics.published_reward_delta;
  const values = [
    0,
    published,
    ...rows.flatMap((row) => [row.point, row.interval[0], row.interval[1]]),
  ];
  const rawMinimum = Math.min(...values);
  const rawMaximum = Math.max(...values);
  const rawSpan = Math.max(rawMaximum - rawMinimum, 0.01);
  const domainMinimum = rawMinimum - rawSpan * 0.08;
  const domainMaximum = rawMaximum + rawSpan * 0.08;
  const domainSpan = domainMaximum - domainMinimum;
  const positionNumber = (value: number) =>
    ((value - domainMinimum) / domainSpan) * 100;
  const position = (value: number) => positionNumber(value) + "%";
  const chartLabel =
    "Published reward delta " +
    formatSigned(published) +
    ". Release sampled estimate " +
    formatSigned(rows[0].point) +
    " with conditional 95 percent interval " +
    conditionalInterval(rows[0].interval) +
    ". Paired deterministic estimate " +
    formatSigned(rows[1].point) +
    " with conditional 95 percent interval " +
    conditionalInterval(rows[1].interval) +
    ".";

  return (
    <figure className="arm-interval-plot">
      <div className="arm-interval-plot__header">
        <div>
          <p className="section-kicker">Conditional uncertainty plot</p>
          <h3 id={"interval-plot-" + arm.arm_id}>
            See the spread before reading the decimals.
          </h3>
          <p>Longer whiskers mean a wider supplied conditional interval.</p>
        </div>
        <div className="arm-interval-plot__legend" aria-hidden="true">
          <span><i className="is-interval" />95% interval</span>
          <span><i className="is-published" />Published Δ</span>
          <span><i className="is-zero" />Zero</span>
        </div>
      </div>
      <div
        aria-label={chartLabel}
        className="arm-interval-plot__chart"
        role="img"
      >
        {rows.map((row) => {
          const low = row.interval[0];
          const high = row.interval[1];
          return (
            <div className="arm-interval-row" key={row.id}>
              <span className="arm-interval-row__label">{row.label}</span>
              <div className="arm-interval-row__scale" aria-hidden="true">
                <i
                  className="arm-interval-row__reference is-zero"
                  style={{ left: position(0) }}
                />
                <i
                  className="arm-interval-row__reference is-published"
                  style={{ left: position(published) }}
                />
                <i
                  className="arm-interval-row__whisker"
                  style={{
                    left: position(low),
                    width:
                      Math.max(positionNumber(high) - positionNumber(low), 0.75) +
                      "%",
                  }}
                />
                <i
                  className="arm-interval-row__cap"
                  style={{ left: position(low) }}
                />
                <i
                  className="arm-interval-row__cap"
                  style={{ left: position(high) }}
                />
                <i
                  className={"arm-interval-row__point is-" + row.id}
                  style={{ left: position(row.point) }}
                />
              </div>
              <code>{formatSigned(row.point)}</code>
            </div>
          );
        })}
      </div>
      <figcaption>
        Points are the supplied endpoints; whiskers are their supplied conditional
        95% intervals. The dashed ice line marks the published delta. This does not
        estimate training-to-training variance.
      </figcaption>
    </figure>
  );
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

export function generateStaticParams() {
  return getStudies().flatMap((study) =>
    study.arms.map((arm) => ({ id: study.study_id, armId: arm.arm_id })),
  );
}

export const dynamicParams = false;

export async function generateMetadata({ params }: ArmPageProps): Promise<Metadata> {
  const { id, armId } = await params;
  const record = getStudyArm(id, armId);
  if (!record) return {};
  const { arm, study } = record;
  return {
    title:
      arm.model_label +
      " · " +
      arm.dataset_label +
      " · arm " +
      arm.ordinal,
    description:
      directionSummary(arm) +
      " Evidence for Study " +
      study.study_id +
      ", Track " +
      arm.track +
      ", seed " +
      arm.seed +
      ".",
    alternates: { canonical: armEvidenceUrl(study.study_id, arm.arm_id) },
  };
}

export default async function ArmEvidencePage({ params }: ArmPageProps) {
  const { id, armId } = await params;
  const record = getStudyArm(id, armId);
  if (!record) notFound();

  const { arm, study } = record;
  const armIndex = study.arms.findIndex((item) => item.arm_id === arm.arm_id);
  const previousArm = study.arms[armIndex - 1];
  const nextArm = study.arms[armIndex + 1];
  const releaseInterval = conditionalInterval(
    arm.metrics.release_prompt_bootstrap_95_ci,
  );
  const pairedInterval = conditionalInterval(
    arm.metrics.independent_paired_bootstrap_95_ci,
  );
  const studyClassification = classificationLabel(study.verdict.classification);

  return (
    <>
      <SiteHeader />
      <StatusStrip study={study} />
      <main id="main-content" className="arm-page">
        <header className="arm-hero">
          <div className="shell">
            <div className="arm-hero__meta">
              <span>STUDY {study.study_id}</span>
              <span>
                ARM {String(arm.ordinal).padStart(3, "0")} / {study.arms.length}
              </span>
            </div>
            <a className="arm-back-link" href={"/studies/" + study.study_id}>
              ← Study record
            </a>
            <p className="section-kicker">Selected arm evidence</p>
            <h1>{arm.model_label} × {arm.dataset_label}</h1>
            <p className="arm-hero__configuration">
              Track {arm.track} · seed {arm.seed} · <code>{arm.arm_id}</code>
            </p>
            <p className="arm-hero__summary">
              This arm tests the {arm.model_label} and {arm.dataset_label} configuration
              under Track {arm.track} at seed {arm.seed}. {directionSummary(arm)}
            </p>

            <div className="arm-outcome-grid">
              <div>
                <span>Arm directional label</span>
                <strong
                  className={
                    "arm-verdict arm-verdict--" + arm.verdict.toLowerCase()
                  }
                >
                  {arm.verdict}
                </strong>
                <small>One arm; not the study classification.</small>
              </div>
              <div>
                <span>Study classification</span>
                <strong className="arm-study-classification">
                  {studyClassification}
                </strong>
                <small>Frozen across all {study.arms.length} selected arms.</small>
              </div>
            </div>

          </div>
        </header>

        <ArmEvidenceTabs>
        <section className="study-section arm-section" id="comparison">
          <div className="shell study-section__grid">
            <div className="study-section__number">01</div>
            <div className="study-section__body">
              <p className="section-kicker">Published versus rerun</p>
              <h2>Numerical inclusion and direction are separate judgments.</h2>
              <div className="arm-metric-grid">
                <article>
                  <span>Published reward Δ</span>
                  <strong>{formatSigned(arm.metrics.published_reward_delta)}</strong>
                  <small>Reported comparison point</small>
                </article>
                <article>
                  <span>Release-protocol reward Δ</span>
                  <strong>{formatSigned(arm.metrics.release_reward_delta)}</strong>
                  <small>Selected sampled endpoint</small>
                </article>
                <article>
                  <span>Conditional 95% interval</span>
                  <strong>{releaseInterval}</strong>
                  <small>Fixed checkpoint and retained generations</small>
                </article>
              </div>

              <ArmIntervalPlot arm={arm} />

              <div className="arm-judgment-grid">
                <article>
                  <span>Numerical interval inclusion</span>
                  <strong>
                    {arm.metrics.published_delta_inside_release_interval
                      ? "Published estimate inside interval"
                      : "Published estimate outside interval"}
                  </strong>
                  <p>
                    This reports only whether the published point estimate falls inside
                    the supplied conditional release interval.
                  </p>
                </article>
                <article>
                  <span>Directional assessment</span>
                  <strong>{directionLabels[arm.metrics.directional_assessment]}</strong>
                  <p>
                    Published as{" "}
                    <code>{arm.metrics.directional_assessment}</code>; this arm-level
                    assessment does not replace the study verdict.
                  </p>
                </article>
              </div>

              <div className="arm-paired-endpoint">
                <div>
                  <p className="section-kicker">Independent paired endpoint</p>
                  <h3>Deterministic comparison, reported independently.</h3>
                  <p>
                    Its within-track Holm-adjusted p-value belongs to this paired
                    endpoint, not to the sampled release endpoint above.
                  </p>
                </div>
                <dl>
                  <div>
                    <dt>Paired reward Δ</dt>
                    <dd>
                      {formatSigned(arm.metrics.independent_paired_reward_delta)}
                    </dd>
                  </div>
                  <div>
                    <dt>Conditional 95% interval</dt>
                    <dd>{pairedInterval}</dd>
                  </div>
                  <div>
                    <dt>Within-track Holm p</dt>
                    <dd>
                      {formatPValue(
                        arm.metrics.independent_paired_sign_flip_pvalue_holm_15,
                      )}
                    </dd>
                  </div>
                </dl>
              </div>
            </div>
          </div>
        </section>

        <section
          className="study-section study-section--tinted arm-section"
          id="execution"
        >
          <div className="shell study-section__grid">
            <div className="study-section__number">02</div>
            <div className="study-section__body">
              <p className="section-kicker">Selected execution</p>
              <h2>The terminal state and recovery flag stay visible.</h2>
              <dl className="arm-fact-list">
                <div>
                  <dt>Selected outcome</dt>
                  <dd>{executionLabels[arm.execution]}</dd>
                </div>
                <div>
                  <dt>Recovery used</dt>
                  <dd>{arm.recovery_used ? "Yes" : "No"}</dd>
                </div>
                <div>
                  <dt>Claim-ready</dt>
                  <dd>{arm.claim_ready ? "Yes" : "No"}</dd>
                </div>
                <div>
                  <dt>Configuration</dt>
                  <dd>
                    {arm.model_label} · {arm.dataset_label} · seed {arm.seed}
                  </dd>
                </div>
                <div>
                  <dt>Claim unit</dt>
                  <dd>
                    Track {arm.track} · arm {String(arm.ordinal).padStart(3, "0")}
                  </dd>
                </div>
              </dl>
              <div className="arm-unavailable" id="attempts">
                <span>ATTEMPT INDEX · NOT YET PUBLIC</span>
                <h3>Deeper evidence is not yet public.</h3>
                <p>
                  Attempt timelines, recovery parents, selection reasons, raw outputs,
                  and per-attempt artifact URLs require the future sanitized{" "}
                  <code>arm-evidence-index.json</code>. No missing history or URL is
                  inferred on this page.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="study-section arm-section" id="provenance">
          <div className="shell study-section__grid">
            <div className="study-section__number">03</div>
            <div className="study-section__body">
              <p className="section-kicker">Hardware and stack provenance</p>
              <h2>Observed hardware, public aliases, explicit profile.</h2>
              <dl className="arm-fact-list">
                <div>
                  <dt>GPU</dt>
                  <dd>{arm.gpu}</dd>
                </div>
                <div>
                  <dt>Neutral host alias</dt>
                  <dd>
                    <code>{arm.host}</code>
                  </dd>
                </div>
                <div>
                  <dt>Stack profile</dt>
                  <dd>
                    <span
                      className={
                        "provenance provenance--" + arm.provenance.toLowerCase()
                      }
                    >
                      {arm.provenance}
                    </span>{" "}
                    {profileDescription(arm)}
                  </dd>
                </div>
                <div>
                  <dt>Protocol</dt>
                  <dd>
                    v{study.protocol.version} · freeze{" "}
                    <code>{study.protocol.freeze_revision}</code>
                  </dd>
                </div>
                <div>
                  <dt>Evidence revision</dt>
                  <dd>
                    <code>{study.source.evidence_revision}</code>
                  </dd>
                </div>
              </dl>
              <p className="study-note">
                The public projection excludes device UUIDs, private paths, raw
                hostnames, service identifiers, addresses, and credentials.
              </p>
            </div>
          </div>
        </section>

        <section
          className="study-section study-section--tinted arm-section"
          id="evidence"
        >
          <div className="shell study-section__grid">
            <div className="study-section__number">04</div>
            <div className="study-section__body">
              <p className="section-kicker">Study-level evidence</p>
              <h2>Hash-bound artifacts supporting this selected arm.</h2>
              <p>
                The current public projection joins this arm to the study bundle by its
                exact <code>arm_id</code>. These are study-level artifacts; direct
                per-attempt and raw-output links are not yet published.
              </p>
              <div
                className="arm-artifact-grid"
                aria-label="Study-level evidence artifacts"
              >
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
              <h2>This page narrows the evidence; it does not widen the claim.</h2>
              <ul className="arm-limit-list">
                <li>This arm contains one registered seed: {arm.seed}.</li>
                <li>
                  Every displayed interval is conditional on fixed checkpoints and
                  retained generations; it is not training-to-training or
                  decoding-to-decoding uncertainty.
                </li>
                <li>
                  <code>{arm.verdict}</code> is an arm-level directional label. The
                  frozen study classification remains{" "}
                  <strong>{studyClassification}</strong>.
                </li>
                <li>
                  Attempt histories and direct raw-output evidence remain unavailable
                  until a sanitized evidence index is published.
                </li>
              </ul>

              <nav
                className="arm-pagination"
                aria-label="Adjacent arm evidence pages"
              >
                {previousArm ? (
                  <a href={armEvidenceUrl(study.study_id, previousArm.arm_id)}>
                    <span>← Previous arm</span>
                    <strong>
                      {String(previousArm.ordinal).padStart(3, "0")} ·{" "}
                      {previousArm.model_label} · {previousArm.dataset_label}
                    </strong>
                  </a>
                ) : (
                  <span />
                )}
                {nextArm ? (
                  <a href={armEvidenceUrl(study.study_id, nextArm.arm_id)}>
                    <span>Next arm →</span>
                    <strong>
                      {String(nextArm.ordinal).padStart(3, "0")} ·{" "}
                      {nextArm.model_label} · {nextArm.dataset_label}
                    </strong>
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
