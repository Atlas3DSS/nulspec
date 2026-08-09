import Link from "next/link";
import { NominationForm } from "@/components/nomination-form";
import { RunLedger } from "@/components/run-ledger";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { StatusStrip } from "@/components/status-strip";
import {
  GITHUB_URL,
  KOFI_URL,
  NOMINATE_URL,
  classificationLabel,
  getLatestStudy,
  protocolUrl,
} from "@/lib/study";

const protocolSteps = [
  {
    number: "01",
    title: "Publish the selection record",
    text: "Every considered paper receives an eligibility result, selection or exclusion reason, resource estimate, and exact-versus-compatible feasibility classification.",
  },
  {
    number: "02",
    title: "Register the protocol",
    text: "The claim scope, comparison rules, decision criteria, exclusions, and maximum escalation budget are committed before full-matrix execution begins.",
  },
  {
    number: "03",
    title: "Run a claim-complete first pass",
    text: "Released-code and manuscript reproductions remain separate from extensions, and every material hardware, software, or implementation deviation is recorded.",
  },
  {
    number: "04",
    title: "Escalate consequential disagreements",
    text: "When stochastic variation could explain a material mismatch, a frozen second stage adds fresh independent repetitions under a predeclared stopping rule.",
  },
  {
    number: "05",
    title: "Publish every terminal outcome",
    text: "Confirming, contradictory, null, failed, and inconclusive outcomes use the same artifact, human-approval, cost-accounting, and independent-rerun requirements.",
  },
];

export default function Home() {
  const study = getLatestStudy();
  const classification = classificationLabel(study.verdict.classification);

  return (
    <>
      <SiteHeader />
      <StatusStrip study={study} />
      <main id="main-content">
        <section className="hero">
          <div className="shell hero__grid">
            <div className="hero__copy">
              <p className="hero__eyebrow">
                <span className="live-dot" aria-hidden="true" />
                Independent computational ML replication
              </p>
              <h1>Published claims, independently tested.</h1>
              <p className="hero__lede">
                NULSPEC reproduces published computational machine-learning
                studies on hardware operated by our team. We publish the full
                selection denominator, frozen protocol, deviations, execution
                evidence, costs, and results—including null and inconclusive ones.
              </p>
              <div className="button-row">
                <a className="button button--primary" href={NOMINATE_URL}>
                  Nominate a paper
                </a>
                <a className="button button--secondary" href={KOFI_URL}>
                  Support replication work
                </a>
              </div>
              <p className="hero__microcopy">
                Funding does not influence paper selection, protocols,
                analysis, or verdicts.
              </p>
            </div>

            <aside className="apparatus" aria-label="Current study summary">
              <div className="apparatus__topline">
                <span>STUDY {study.study_id}</span>
                <span>REPORTED</span>
              </div>
              <p className="apparatus__title">
                Small-model reinforcement learning
              </p>
              <dl className="apparatus__facts">
                <div>
                  <dt>Matrix</dt>
                  <dd>{study.completion.registered_arms} arms · {study.completion.tracks.length} tracks</dd>
                </div>
                <div>
                  <dt>Compute</dt>
                  <dd>3090 · 4090 · PRO 6000</dd>
                </div>
                <div>
                  <dt>Protocol</dt>
                  <dd>v{study.protocol.version} frozen</dd>
                </div>
                <div>
                  <dt>Conclusion</dt>
                  <dd>{classification}</dd>
                </div>
              </dl>
              <div className="apparatus__signal" aria-hidden="true">
                {study.arms.map((arm) => (
                  <span
                    className={`apparatus__tick apparatus__tick--${arm.state.toLowerCase()}`}
                    key={arm.arm_id}
                  />
                ))}
              </div>
              <Link href={`/studies/${study.study_id}`}>
                View Study {study.study_id} →
              </Link>
            </aside>
          </div>
        </section>

        <section className="statement" id="about">
          <div className="shell statement__grid">
            <p className="section-kicker">Purpose</p>
            <div>
              <h2>
                We identify which published findings hold, fail, or remain
                uncertain.
              </h2>
              <p>
                NULSPEC is an independent computational ML replication program.
                We operate the compute directly and publish the evidence needed
                to assess each result, including why a paper entered the queue
                and why another paper did not.
              </p>
              <p>
                The near-term objective is deliberately narrow: become very good
                at computational ML replication and build a uniform corpus of
                finished external claims. That corpus can eventually test which
                research practices—code release, dependency locks, evaluation
                design, paper age, or hardware portability—predict reliability.
              </p>
            </div>
          </div>
        </section>

        <section className="method-section" id="method">
          <div className="shell">
            <div className="section-heading">
              <p className="section-kicker">Replication workflow</p>
              <h2>How each study is specified, executed, and reported</h2>
              <p>
                Each publication includes its selection provenance, registered
                protocol, execution status, documented deviations, analysis
                code, final cost state, and a verdict limited to the available
                evidence.
              </p>
            </div>
            <ol className="protocol-list">
              {protocolSteps.map((step) => (
                <li key={step.number}>
                  <span>{step.number}</span>
                  <h3>{step.title}</h3>
                  <p>{step.text}</p>
                </li>
              ))}
            </ol>
            <div className="plain-link-row">
              <Link href="/methodology">Read the full methodology →</Link>
              <Link href="/selection">Audit paper selection →</Link>
              <a href={protocolUrl(study)}>Read the frozen protocol ↗</a>
              <a href={GITHUB_URL}>Audit the repository ↗</a>
            </div>
          </div>
        </section>

        <section className="study-preview" id="study-001">
          <div className="shell">
            <div className="study-preview__intro">
              <div>
                <p className="section-kicker">Reported · Study {study.study_id}</p>
                <h2>{study.study.paper.title}</h2>
              </div>
              <p>
                <strong>{study.verdict.headline}</strong>{" "}
                {study.verdict.summary}
              </p>
            </div>
            <RunLedger study={study} compact />
            <div className="plain-link-row">
              <Link href={`/studies/${study.study_id}`}>
                Open the complete study record →
              </Link>
              <a href={study.study.paper.url}>
                Read arXiv:{study.study.paper.arxiv_id} ↗
              </a>
            </div>
          </div>
        </section>

        <section className="principles">
          <div className="shell principles__grid">
            <blockquote>
              <span aria-hidden="true">∅</span>
              <p>Null and inconclusive outcomes are retained and published.</p>
            </blockquote>
            <blockquote>
              <span aria-hidden="true">D-</span>
              <p>
                Material deviations are documented with their effect on
                interpretation.
              </p>
            </blockquote>
            <blockquote>
              <span aria-hidden="true">git</span>
              <p>
                Commands, revisions, and artifact hashes support independent
                verification.
              </p>
            </blockquote>
          </div>
        </section>

        <section className="request-section" id="nominate">
          <div className="shell request-section__grid">
            <div>
              <p className="section-kicker">Paper nominations</p>
              <h2>Nominate an arXiv paper for replication</h2>
              <p>
                We currently accept computational ML papers that can be assessed
                against public eligibility and resource rules. Nominations and
                votes record public interest; they do not determine eligibility,
                protocols, analysis, or verdicts. Every considered paper enters
                the public selection ledger.
              </p>
              <p className="request-section__privacy">
                The form requires an email address and an arXiv URL.
                Nominations are sent to a private Discord channel accessible to
                Atlas staff. If we complete and publish a replication, we may
                use the address to send one email with the result.
              </p>
              <p className="request-section__candidate-link">
                <Link href="/papers">Review and vote on nominated papers →</Link>
                {" · "}
                <Link href="/selection">Audit selection decisions →</Link>
              </p>
            </div>
            <NominationForm />
          </div>
        </section>

        <section className="support-section">
          <div className="shell support-section__inner">
            <p className="section-kicker">Support replication work</p>
            <h2>Funding increases replication capacity</h2>
            <p>
              Contributions fund compute time, storage, and research labor.
              Funding does not affect protocols, analysis, or verdicts.
              Additional resources allow the team to replicate more papers and
              complete follow-up experiments sooner.
            </p>
            <a className="button button--secondary" href={KOFI_URL}>
              Support NULSPEC on Ko-fi
            </a>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
