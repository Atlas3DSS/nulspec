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
    title: "Freeze the specification",
    text: "The protocol, comparison rules, and exclusions enter Git before the first full-matrix run.",
  },
  {
    number: "02",
    title: "Reproduce before extending",
    text: "Released code and manuscript-faithful interpretations stay separate. New ideas cannot rewrite the primary result.",
  },
  {
    number: "03",
    title: "Number every deviation",
    text: "Hardware, stack, and implementation substitutions get an ID, a reason, and an impact control.",
  },
  {
    number: "04",
    title: "Publish the miss",
    text: "Failures, null results, and irreproducible recipes receive the same artifact trail as a match.",
  },
  {
    number: "05",
    title: "Make rerunning cheaper",
    text: "Commands, digests, checkpoints, and analysis code are preserved so the next person starts ahead of us.",
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
                Independent research replication
              </p>
              <h1>We rerun the experiments.</h1>
              <p className="hero__lede">
                NULSPEC independently replicates published AI research on
                hardware we control—and publishes the run ledger in public
                before we know how it ends.
              </p>
              <div className="button-row">
                <a className="button button--primary" href={NOMINATE_URL}>
                  Nominate a paper
                </a>
                <a className="button button--secondary" href={KOFI_URL}>
                  Fund GPU-hours
                </a>
              </div>
              <p className="hero__microcopy">
                No pay-to-confirm. No hidden reruns. No success-only drawer.
              </p>
            </div>

            <aside className="apparatus" aria-label="Current study apparatus">
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
                Inspect Study {study.study_id} →
              </Link>
            </aside>
          </div>
        </section>

        <section className="statement" id="about">
          <div className="shell statement__grid">
            <p className="section-kicker">What this is</p>
            <div>
              <h2>
                Independent replication, done by people curious enough to
                check.
              </h2>
              <p>
                NULSPEC is a small team of enthusiasts and{" "}
                <strong>accelerationalists</strong>. We want the field to move
                fast, and we think the fastest route runs through checking the
                work.
              </p>
              <p>
                We reproduce recent papers on our own machines, freeze the
                protocol before the first run, and publish the ledger whether
                or not the result cooperates.
              </p>
            </div>
          </div>
        </section>

        <section className="method-section" id="method">
          <div className="shell">
            <div className="section-heading">
              <p className="section-kicker">Our operating protocol</p>
              <h2>The artifact is the argument.</h2>
              <p>
                A paper is not a vibe. A replication should leave enough
                evidence for a stranger to disagree productively.
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
              <p>A null result is a result.</p>
            </blockquote>
            <blockquote>
              <span aria-hidden="true">D-</span>
              <p>A deviation hidden is a claim faked.</p>
            </blockquote>
            <blockquote>
              <span aria-hidden="true">git</span>
              <p>If you cannot rerun it, you are reading marketing.</p>
            </blockquote>
          </div>
        </section>

        <section className="request-section" id="nominate">
          <div className="shell request-section__grid">
            <div>
              <p className="section-kicker">Put a claim on the bench</p>
              <h2>Seen a result you want tested?</h2>
              <p>
                Nominate it. We choose papers we can honestly attempt on local
                compute and a fixed budget. If we take yours on, the protocol
                goes public before the first arm launches—and so does every
                deviation we are forced to make.
              </p>
              <p className="request-section__privacy">
                Two fields, no account. We retain the nomination in a private
                Atlas staff channel and use your email only if we choose to
                respond.
              </p>
            </div>
            <NominationForm />
          </div>
        </section>

        <section className="support-section">
          <div className="shell support-section__inner">
            <p className="section-kicker">Keep the apparatus alive</p>
            <h2>Support buys compute, not conclusions.</h2>
            <p>
              Donations go to GPU-hours, storage, and time. They cannot touch a
              verdict: protocols and decision rules are frozen before analysis.
              If you want more papers checked, faster, buy the lab monkey a
              little more runway.
            </p>
            <a className="button button--secondary" href={KOFI_URL}>
              Fund GPU-hours on Ko-fi
            </a>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
