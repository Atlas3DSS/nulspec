import type { Metadata } from "next";
import { RunLedger } from "@/components/run-ledger";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { StatusStrip } from "@/components/status-strip";
import { StudyStateRail } from "@/components/study-state-rail";
import {
  GITHUB_URL,
  KOFI_URL,
  NOMINATE_URL,
  PROTOCOL_URL,
  formatAsOf,
  study,
} from "@/lib/study";

export const metadata: Metadata = {
  title: "Study 001",
  description:
    "Live, 15-configuration reproduction of arXiv:2607.25091, with exact-stack and Blackwell-compatible provenance kept explicit.",
  alternates: {
    canonical: "/studies/001",
  },
};

const stackRows = [
  {
    hardware: "RTX 3090 · 24 GB",
    host: "wtatum84",
    profile: "EXACT",
    role: "Paper-pinned Ampere execution",
  },
  {
    hardware: "RTX 4090 · 24 GB",
    host: "MonkeyPC",
    profile: "EXACT",
    role: "Paper-pinned Ada execution",
  },
  {
    hardware: "RTX PRO 6000 · 96 GB",
    host: "wtatum84",
    profile: "COMPAT",
    role: "Blackwell throughput; exact-stack re-evaluation required",
  },
];

export default function Study001Page() {
  return (
    <>
      <SiteHeader />
      <StatusStrip />
      <main id="main-content" className="study-page">
        <header className="study-hero">
          <div className="shell">
            <div className="study-hero__meta">
              <span>STUDY 001</span>
              <span>AS OF {formatAsOf(study.as_of_utc).toUpperCase()} UTC</span>
            </div>
            <p className="hero__eyebrow">
              <span className="live-dot" aria-hidden="true" />
              {study.state}
              <span className="live-caret" aria-hidden="true">
                ▌
              </span>
            </p>
            <h1>{study.paper.title}</h1>
            <p className="study-hero__citation">
              arXiv:{study.paper.arxiv_id} · released source{" "}
              <code>{study.paper.source_commit.slice(0, 12)}</code>
            </p>
            <div className="plain-link-row">
              <a href={study.paper.url}>Original paper ↗</a>
              <a href={PROTOCOL_URL}>Frozen protocol ↗</a>
              <a href={GITHUB_URL}>Repository ↗</a>
            </div>
            <StudyStateRail current={study.state} />
          </div>
        </header>

        <section className="study-section">
          <div className="shell study-section__grid">
            <div className="study-section__number">01</div>
            <div className="study-section__body">
              <p className="section-kicker">Claim under test</p>
              <h2>Does capacity headroom predict where PPO helps?</h2>
              <p className="study-section__lead">{study.claim_under_test}</p>
              <p>
                This is a claim-level matrix test, not a search for one favorable
                checkpoint. Numerical, directional, and family-wise assessments
                are specified in advance. The overall interpretation remains
                locked until all 15 Track R arms complete.
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
                  <dt>Protocol</dt>
                  <dd>{study.protocol.tag}</dd>
                </div>
                <div>
                  <dt>Freeze commit</dt>
                  <dd>
                    <code>{study.protocol.freeze_commit}</code>
                  </dd>
                </div>
                <div>
                  <dt>Matrix SHA-256</dt>
                  <dd>
                    <code>{study.protocol.matrix_sha256}</code>
                  </dd>
                </div>
                <div>
                  <dt>Config SHA-256</dt>
                  <dd>
                    <code>{study.protocol.config_sha256}</code>
                  </dd>
                </div>
              </dl>
              <p>
                Track R follows the released 250-step recipe. Track M separately
                tests manuscript-stated operations contradicted or absent in the
                executable release. Extensions cannot alter either primary
                track.
              </p>
            </div>
          </div>
        </section>

        <section className="study-section">
          <div className="shell study-section__grid">
            <div className="study-section__number">03</div>
            <div className="study-section__body">
              <p className="section-kicker">Hardware and stack provenance</p>
              <h2>Three cards, two execution profiles.</h2>
              <div className="table-scroll" tabIndex={0}>
                <table className="hardware-table">
                  <thead>
                    <tr>
                      <th scope="col">Hardware</th>
                      <th scope="col">Host</th>
                      <th scope="col">Profile</th>
                      <th scope="col">Role</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stackRows.map((row) => (
                      <tr key={row.hardware}>
                        <th scope="row">{row.hardware}</th>
                        <td>
                          <code>{row.host}</code>
                        </td>
                        <td>
                          <span
                            className={`provenance provenance--${row.profile.toLowerCase()}`}
                          >
                            {row.profile}
                          </span>
                        </td>
                        <td>{row.role}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="study-note">
                Faster hardware changes wall time, not the frozen data, seed,
                hyperparameters, or evaluation. The execution profile remains
                attached to every arm.
              </p>
            </div>
          </div>
        </section>

        <section className="study-section study-section--ledger">
          <div className="shell study-section__grid">
            <div className="study-section__number">04</div>
            <div className="study-section__body">
              <RunLedger />
            </div>
          </div>
        </section>

        <section className="study-section">
          <div className="shell study-section__grid">
            <div className="study-section__number">05</div>
            <div className="study-section__body">
              <p className="section-kicker">Deviation register</p>
              <h2>Append-only by design.</h2>
              <ol className="deviation-list">
                {study.deviations.map((deviation) => (
                  <li key={deviation.id}>
                    <div>
                      <span>{deviation.id}</span>
                      <span>{deviation.scope}</span>
                    </div>
                    <p>{deviation.what}</p>
                    <p>
                      <strong>Control:</strong> {deviation.impact_control}
                    </p>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </section>

        <section className="study-section results-gate">
          <div className="shell study-section__grid">
            <div className="study-section__number">06</div>
            <div className="study-section__body">
              <p className="section-kicker">Results · gated</p>
              <h2>No claim-level result yet.</h2>
              <p className="study-section__lead">
                Publishing a moving conclusion would turn queue order into a
                scientific choice. The run ledger above is the only live status
                we report.
              </p>
              <p>
                When all 15 arms finish, this gate opens first to the frozen
                analysis, then to an explicit conclusion: reproduced, partially
                reproduced, not reproduced, or inconclusive. Null results remain
                first-class results.
              </p>
            </div>
          </div>
        </section>

        <section className="study-section extension-fence">
          <div className="shell study-section__grid">
            <div className="study-section__number">EXT</div>
            <div className="study-section__body">
              <p className="section-kicker">Local-compute extensions</p>
              <h2>Interesting, separate, unable to rewrite the replication.</h2>
              <p>
                After the paper-faithful matrix, we will test manuscript/code
                mismatches, local judges, readiness signals, and an outer
                teacher that reviews the Qwen 27B reviewer. These are fenced
                from primary outcomes in protocol and storage.
              </p>
              <ul className="extension-list">
                <li>manuscript-faithful reward initialization and dtype;</li>
                <li>Qwen 27B pairwise review of much smaller agents;</li>
                <li>Codex outer-teacher audit of the reviewer;</li>
                <li>additional seeds and stability diagnostics where justified.</li>
              </ul>
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
              <a className="button button--primary" href={NOMINATE_URL}>
                Nominate the next paper
              </a>
              <a className="button button--secondary" href={KOFI_URL}>
                Fund GPU-hours
              </a>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
