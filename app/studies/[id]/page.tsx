import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { RunLedger } from "@/components/run-ledger";
import { ExtensionVoteForm } from "@/components/extension-vote-form";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { StatusStrip } from "@/components/status-strip";
import { StudyStateRail } from "@/components/study-state-rail";
import {
  GITHUB_URL,
  KOFI_URL,
  NOMINATE_URL,
  artifactUrl,
  classificationLabel,
  formatAsOf,
  getStudies,
  getStudy,
  protocolUrl,
  type PublicationArtifact,
  type StudyDocument,
} from "@/lib/study";

type StudyPageProps = {
  params: Promise<{ id: string }>;
};

const artifactLabels: Record<string, string> = {
  result_summary: "Result summary",
  full_report: "Full matrix report",
  machine_analysis: "Machine-readable analysis",
  extension_roadmap: "Extension roadmap",
  website_handoff: "Website handoff contract",
  frontend_handoff: "Arm evidence specification",
};

export function generateStaticParams() {
  return getStudies().map((study) => ({ id: study.study_id }));
}

export const dynamicParams = false;

export async function generateMetadata({ params }: StudyPageProps): Promise<Metadata> {
  const { id } = await params;
  const study = getStudy(id);
  if (!study) return {};
  return {
    title: `Study ${study.study_id}: ${classificationLabel(study.verdict.classification)}`,
    description: study.verdict.summary,
    alternates: { canonical: `/studies/${study.study_id}` },
  };
}

function hardwareRows(study: StudyDocument) {
  const rows = new Map<string, { hardware: string; host: string; profile: string }>();
  for (const arm of study.arms) {
    const key = `${arm.host}|${arm.gpu}|${arm.provenance}`;
    rows.set(key, {
      hardware: arm.gpu,
      host: arm.host.toUpperCase().replaceAll("-", " "),
      profile: arm.provenance,
    });
  }
  return [...rows.values()];
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

export default async function StudyPage({ params }: StudyPageProps) {
  const { id } = await params;
  const study = getStudy(id);
  if (!study) notFound();
  const rows = hardwareRows(study);
  const classification = classificationLabel(study.verdict.classification);

  return (
    <>
      <SiteHeader />
      <StatusStrip study={study} />
      <main id="main-content" className="study-page">
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
            <h1>{study.study.paper.title}</h1>
            <p className="study-hero__citation">
              arXiv:{study.study.paper.arxiv_id} · evidence revision{" "}
              <code>{study.source.evidence_revision.slice(0, 12)}</code>
            </p>
            <div className="plain-link-row">
              <a href={study.study.paper.url}>Original paper ↗</a>
              <a href={protocolUrl(study)}>Frozen protocol ↗</a>
              <a href={GITHUB_URL}>Public record ↗</a>
            </div>
            <StudyStateRail current={study.state} />
          </div>
        </header>

        <section className="study-section">
          <div className="shell study-section__grid">
            <div className="study-section__number">01</div>
            <div className="study-section__body">
              <p className="section-kicker">Claim under test</p>
              <h2>A complete matrix, not a favorable checkpoint.</h2>
              <p className="study-section__lead">{study.study.claim_under_test}</p>
              <p>
                The registered family contains {study.completion.registered_arms} selected
                arms across {study.completion.tracks.length} separately interpreted tracks.
                Every selected arm reached a terminal, claim-ready state before the verdict
                gate opened.
              </p>
            </div>
          </div>
        </section>

        <section className="study-section study-section--tinted">
          <div className="shell study-section__grid">
            <div className="study-section__number">02</div>
            <div className="study-section__body">
              <p className="section-kicker">Frozen protocol</p>
              <h2>“Exact” is a versioned statement.</h2>
              <dl className="digest-list">
                <div>
                  <dt>Execution protocol</dt>
                  <dd>v{study.protocol.version}</dd>
                </div>
                <div>
                  <dt>Freeze revision</dt>
                  <dd><code>{study.protocol.freeze_revision}</code></dd>
                </div>
                <div>
                  <dt>Matrix SHA-256</dt>
                  <dd><code>{study.protocol.matrix_sha256}</code></dd>
                </div>
                <div>
                  <dt>Config SHA-256</dt>
                  <dd><code>{study.protocol.config_sha256}</code></dd>
                </div>
              </dl>
              <div className="track-cards">
                {study.completion.tracks.map((track) => (
                  <div key={track.id}>
                    <span>TRACK {track.id}</span>
                    <strong>{track.label ?? `Track ${track.id}`}</strong>
                    <p>{track.claim_ready_arms}/{track.registered_arms} claim-ready</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="study-section">
          <div className="shell study-section__grid">
            <div className="study-section__number">03</div>
            <div className="study-section__body">
              <p className="section-kicker">Hardware and stack provenance</p>
              <h2>Observed hardware, neutral lab identities.</h2>
              <div className="table-scroll" tabIndex={0}>
                <table className="hardware-table">
                  <thead>
                    <tr>
                      <th scope="col">Hardware</th>
                      <th scope="col">Host</th>
                      <th scope="col">Profile</th>
                      <th scope="col">Interpretation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => (
                      <tr key={`${row.host}-${row.hardware}-${row.profile}`}>
                        <th scope="row">{row.hardware}</th>
                        <td><code>{row.host}</code></td>
                        <td>
                          <span className={`provenance provenance--${row.profile.toLowerCase()}`}>
                            {row.profile}
                          </span>
                        </td>
                        <td>
                          {row.profile === "EXACT"
                            ? "Paper-pinned execution profile"
                            : "Compatibility training; exact-stack claim evaluation"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="study-note">
                The publication export contains observed GPU labels and neutral host aliases.
                Device UUIDs, private paths, and unrelated operational records are excluded.
              </p>
            </div>
          </div>
        </section>

        <section className="study-section study-section--ledger">
          <div className="shell study-section__grid">
            <div className="study-section__number">04</div>
            <div className="study-section__body">
              <RunLedger study={study} />
            </div>
          </div>
        </section>

        <section className="study-section">
          <div className="shell study-section__grid">
            <div className="study-section__number">05</div>
            <div className="study-section__body">
              <p className="section-kicker">Deviation register</p>
              <h2>Material differences stay attached to the result.</h2>
              <ol className="deviation-list">
                {study.deviations.map((deviation) => (
                  <li key={deviation.id}>
                    <div>
                      <span>{deviation.id}</span>
                      <span>{deviation.scope}</span>
                    </div>
                    <p>{deviation.description}</p>
                    <p><strong>Control:</strong> {deviation.control}</p>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </section>

        <section className="study-section results-reported">
          <div className="shell study-section__grid">
            <div className="study-section__number">06</div>
            <div className="study-section__body">
              <p className="section-kicker">Results · reported</p>
              <span className={`result-classification result-classification--${study.verdict.classification.toLowerCase()}`}>
                {classification}
              </span>
              <h2>{study.verdict.headline}</h2>
              <p className="study-section__lead">{study.verdict.summary}</p>

              <div className="result-columns">
                <div>
                  <h3>What the evidence says</h3>
                  <ul>
                    {study.verdict.key_findings.map((finding) => <li key={finding}>{finding}</li>)}
                  </ul>
                </div>
                <div>
                  <h3>Limits on the claim</h3>
                  <ul>
                    {study.verdict.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
                  </ul>
                </div>
              </div>

              <div className="result-artifacts" aria-label="Published result artifacts">
                {study.artifacts.map((artifact) => (
                  <ArtifactLink artifact={artifact} key={artifact.role} />
                ))}
              </div>
              <p className="result-provenance">
                Public bundle bound to evidence revision{" "}
                <code>{study.source.evidence_revision}</code>. Artifact links are verified
                against the SHA-256 digests shown above before deployment.
              </p>
            </div>
          </div>
        </section>

        <section className="study-section extension-fence">
          <div className="shell study-section__grid">
            <div className="study-section__number">EXT</div>
            <div className="study-section__body">
              <p className="section-kicker">Extensions remain fenced</p>
              <h2>New evidence may extend this record, never rewrite it.</h2>
              <p>
                Reviewer diagnostics, additional seeds, ablations, and future hardware
                sensitivity checks remain separate from this frozen primary verdict.
                Any extension receives its own provenance and cannot silently change the
                completed run manifest.
              </p>
              {study.frozen_primary_result && (
                <p className="extension-fence__lock">
                  FROZEN PRIMARY RESULT · {study.frozen_primary_result.claim_ready_arms}/
                  {study.frozen_primary_result.registered_arms} CLAIM-READY · REWRITABLE: NO
                </p>
              )}
              {study.extension_call_to_action && (
                <ExtensionVoteForm
                  callToAction={study.extension_call_to_action}
                  studyId={study.study_id}
                />
              )}
            </div>
          </div>
        </section>

        <section className="study-cta">
          <div className="shell study-cta__grid">
            <div>
              <p className="section-kicker">Follow or challenge the work</p>
              <h2>Every useful objection should become a reproducible test.</h2>
            </div>
            <div className="button-row">
              <a className="button button--primary" href={NOMINATE_URL}>Nominate the next paper</a>
              <a className="button button--secondary" href={KOFI_URL}>Fund GPU-hours</a>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
