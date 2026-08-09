import type { Metadata } from "next";
import Link from "next/link";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { StatusStrip } from "@/components/status-strip";
import { getSelectionLedger } from "@/lib/selection-ledger";
import { getLatestStudy } from "@/lib/study";

export const dynamic = "force-static";

export const metadata: Metadata = {
  title: "Methodology",
  description:
    "NULSPEC's prospective paper-selection, randomized sampling, statistical escalation, audit, and replication-quota rules.",
  alternates: { canonical: "/methodology" },
  openGraph: {
    title: "Replication methodology — NULSPEC",
    description:
      "Public rules for selecting computational ML claims, escalating stochastic disagreements, and counting finished replications.",
    url: "/methodology",
  },
};

const pipeline = [
  {
    id: "01",
    title: "Log every candidate",
    text: "Publish the claim, selection state, reasons, cost estimate, and exact-versus-compatible assessment—even when the paper is deferred or rejected.",
  },
  {
    id: "02",
    title: "Apply objective eligibility",
    text: "Require an external empirical claim, a falsifiable endpoint, auditable inputs, current-domain fit, and a claim-complete design inside a declared resource envelope.",
  },
  {
    id: "03",
    title: "Allocate a selection slot",
    text: "Within each prospective block of three starts, two may be priority-selected and at least one is drawn reproducibly from an eligible resource-matched pool.",
  },
  {
    id: "04",
    title: "Freeze before full execution",
    text: "Commit the protocol, claim boundaries, verdict rules, exclusions, deviations, and maximum escalation budget before observing the full result.",
  },
  {
    id: "05",
    title: "Escalate material disagreements",
    text: "Treat the first pass as triage. When stochastic variation could explain a consequential mismatch, freeze and run fresh independent repetitions.",
  },
  {
    id: "06",
    title: "Publish and count only finished work",
    text: "A study joins the NULSPEC 20 only after terminal artifacts, analysis, automated QA, human approval, public release, and final cost accounting or an explicit pending audit.",
  },
];

const escalation = [
  {
    stage: "Stage 1",
    title: "Claim-complete first pass",
    text: "Run the cheapest frozen matrix that can evaluate the primary claim. Match the paper's repetition count when feasible, but do not call a one-realization disagreement a definitive failure.",
  },
  {
    stage: "Trigger",
    title: "Material and plausibly stochastic discordance",
    text: "Escalation is mandatory when the result changes a headline direction or crosses a declared materiality boundary and training, sampling, decoding, or data order could plausibly explain it.",
  },
  {
    stage: "Stage 2",
    title: "Fresh independent repetitions",
    text: "Freeze the estimand, repetition unit, uncertainty method, stopping rule, and maximum budget. Run at least three fresh repetitions per disputed condition, or the paper's larger declared count.",
  },
  {
    stage: "Terminal rule",
    title: "Inconclusive remains available",
    text: "If the frozen maximum budget cannot resolve the relevant uncertainty, report the result as limited or inconclusive. No favorable optional stopping is permitted.",
  },
];

export default function MethodologyPage() {
  const study = getLatestStudy();
  const ledger = getSelectionLedger();

  return (
    <>
      <SiteHeader />
      <StatusStrip study={study} />
      <main id="main-content" className="policy-page">
        <section className="policy-hero">
          <div className="shell policy-hero__grid">
            <div>
              <p className="hero__eyebrow">Methodology v{ledger.methodology_version}</p>
              <h1>From isolated replications to an interpretable corpus.</h1>
              <p className="policy-hero__lede">
                Rigorous execution is not enough if paper selection is opaque or
                stochastic disagreements are underpowered. These prospective rules
                publish the intake denominator, introduce randomized selection, and
                direct extra compute to results where it can change the conclusion.
              </p>
              <div className="button-row">
                <Link className="button button--primary" href="/selection">
                  Open selection ledger
                </Link>
                <a
                  className="button button--secondary"
                  href="https://github.com/Atlas3DSS/nulspec/blob/main/docs/SELECTION_AND_ESCALATION_POLICY.md"
                >
                  Versioned policy ↗
                </a>
              </div>
            </div>
            <dl className="policy-facts">
              <div>
                <dt>Current scope</dt>
                <dd>{ledger.scope.active_domain}</dd>
              </div>
              <div>
                <dt>Randomized starts</dt>
                <dd>At least 1 in every 3</dd>
              </div>
              <div>
                <dt>Corpus target</dt>
                <dd>{ledger.summary.quota_target} finished external claims</dd>
              </div>
              <div>
                <dt>Model-audit weight</dt>
                <dd>Zero scientific weight</dd>
              </div>
            </dl>
          </div>
        </section>

        <section className="policy-notice">
          <div className="shell">
            <strong>Prospective boundary.</strong>{" "}
            Current intake predates this randomized policy. The first 12 records are
            labeled as a pre-policy convenience intake and will never be used as if
            they were a probability sample.
          </div>
        </section>

        <section className="policy-section">
          <div className="shell">
            <div className="section-heading">
              <p className="section-kicker">Selection pipeline</p>
              <h2>Every considered paper leaves a public trace</h2>
              <p>
                Selection decisions are evidence too. The ledger preserves the
                denominator needed to distinguish paper-level findings from broader
                statements about ML research reliability.
              </p>
            </div>
            <ol className="policy-step-list">
              {pipeline.map((step) => (
                <li key={step.id}>
                  <span>{step.id}</span>
                  <div>
                    <h3>{step.title}</h3>
                    <p>{step.text}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="policy-section policy-section--tinted">
          <div className="shell policy-grid">
            <div>
              <p className="section-kicker">Eligibility</p>
              <h2>Rules applied before priority or randomness</h2>
              <p className="policy-lede">
                Public code helps but is not mandatory. A manuscript reconstruction
                can qualify when assumptions are bounded; missing evidence can make
                an exact stage infeasible without making the candidate disappear.
              </p>
            </div>
            <ol className="eligibility-list">
              {ledger.eligibility_rules.map((rule) => (
                <li key={rule.id}>
                  <span>{rule.id}</span>
                  <div>
                    <h3>{rule.label}</h3>
                    <p>{rule.rule}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="policy-section">
          <div className="shell">
            <div className="section-heading">
              <p className="section-kicker">Sampling</p>
              <h2>One reproducible draw per three new starts</h2>
              <p>
                The draw is made only after the eligible pool and compute band are
                frozen. Priority selection remains available, but it can no longer
                define the entire corpus.
              </p>
            </div>
            <div className="draw-contract">
              <div>
                <span>01 · Freeze</span>
                <p>{ledger.randomized_selection.pool_rule}</p>
              </div>
              <div>
                <span>02 · Draw</span>
                <p>{ledger.randomized_selection.draw_rule}</p>
              </div>
              <div>
                <span>03 · Preserve</span>
                <p>{ledger.randomized_selection.replacement_rule}</p>
              </div>
            </div>
          </div>
        </section>

        <section className="policy-section policy-section--tinted">
          <div className="shell">
            <div className="section-heading">
              <p className="section-kicker">Statistical escalation</p>
              <h2>The cheap run is triage, not always the final court</h2>
              <p>
                Compute is concentrated where extra repetitions can distinguish a
                fragile mismatch from a stable disagreement.
              </p>
            </div>
            <ol className="escalation-grid">
              {escalation.map((item) => (
                <li key={item.stage}>
                  <span>{item.stage}</span>
                  <h3>{item.title}</h3>
                  <p>{item.text}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="policy-section">
          <div className="shell audit-boundary">
            <div>
              <p className="section-kicker">Release QA boundary</p>
              <h2>Models check the packet. They do not validate the science.</h2>
            </div>
            <div>
              <p className="policy-lede">
                Automated consistency audits have zero scientific decision weight.
                They check required fields, internal consistency, trace bindings,
                and obvious scope errors. Agreement between two models is not peer
                review, independent domain expertise, or another replication.
              </p>
              <p>
                An audit can keep a release blocked for human inspection. It cannot
                upgrade a result. Publication requires a separate human decision on
                the immutable release packet, and author communication requires its
                own human approval.
              </p>
            </div>
          </div>
        </section>

        <section className="policy-section policy-section--corpus">
          <div className="shell corpus-callout">
            <p className="section-kicker">NULSPEC 20</p>
            <h2>Twenty finished external claims—not twenty interesting projects.</h2>
            <p>
              Only an externally published claim that completes the uniform protocol,
              artifact, analysis, audit, human-approval, and public-release process
              counts. Extensions, original VLM or J-space work, tools, and unfinished
              attempts stay valuable, but they remain outside the quota.
            </p>
            <Link href="/selection">
              See the denominator, estimates, exclusions, and current count →
            </Link>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
