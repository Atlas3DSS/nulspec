import type { Metadata } from "next";
import Link from "next/link";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { getFableRefusalLedger } from "@/lib/fable-refusals";

export const dynamic = "force-static";

export const metadata: Metadata = {
  title: "Operations ledger",
  description:
    "Append-only records of NULSPEC infrastructure, provider, integration, and release-process incidents.",
  alternates: { canonical: "/operations" },
  openGraph: {
    title: "Operations ledger — NULSPEC",
    description:
      "Operational incidents are retained for reproducibility without being presented as scientific findings.",
    url: "/operations",
  },
};

const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 6,
});

export default function OperationsPage() {
  const ledger = getFableRefusalLedger();
  const incident = ledger.refusals[0];

  return (
    <>
      <SiteHeader />
      <main id="main-content" className="operations-page">
        <section className="operations-hero">
          <div className="shell operations-hero__grid">
            <div>
              <p className="hero__eyebrow">Operational transparency</p>
              <h1>Incidents belong in the record, not in the scientific result.</h1>
              <p className="operations-hero__lede">
                This ledger retains provider failures, integration errors, recovery
                attempts, costs, and trace hashes. Incidents can improve the process;
                they do not provide evidence for or against a paper&apos;s claim.
              </p>
            </div>
            <dl className="operations-summary">
              <div>
                <dt>Recorded incidents</dt>
                <dd>{ledger.summary.refusal_count}</dd>
              </div>
              <div>
                <dt>Scientific weight</dt>
                <dd>0</dd>
              </div>
              <div>
                <dt>Provider charges</dt>
                <dd>{money.format(ledger.summary.total_charged_usd)}</dd>
              </div>
            </dl>
          </div>
        </section>

        <section className="operations-ledger shell" aria-labelledby="operations-ledger-heading">
          <div className="section-heading">
            <p className="section-kicker">Append-only incident log</p>
            <h2 id="operations-ledger-heading">Recorded events</h2>
            <p>
              Provider and NULSPEC-attributable failures are kept under the same
              evidence standard. Corrections append; original traces remain bound by
              hash.
            </p>
          </div>
          <article className="incident-record">
            <div className="incident-record__meta">
              <span>{incident.id}</span>
              <time dateTime={incident.occurred_at_utc}>
                {new Date(incident.occurred_at_utc).toLocaleDateString("en-US", {
                  dateStyle: "long",
                  timeZone: "UTC",
                })}
              </time>
            </div>
            <div className="incident-record__body">
              <div>
                <p className="section-kicker">Provider non-response</p>
                <h3>Fable model-audit request returned no substantive output</h3>
                <p>
                  A paid release-consistency request ended in a safeguard refusal.
                  NULSPEC&apos;s integration errors, subsequent model-audit attempts,
                  cost, hashes, and publication delay are preserved in the detailed
                  record.
                </p>
              </div>
              <dl>
                <div><dt>Scientific effect</dt><dd>None</dd></div>
                <div><dt>Process effect</dt><dd>Publication delayed</dd></div>
                <div><dt>Current state</dt><dd>Historical; policy superseded</dd></div>
              </dl>
            </div>
            <Link href="/fable-refusals">Open the complete archived incident →</Link>
          </article>
        </section>

        <section className="operations-boundary">
          <div className="shell audit-boundary">
            <div>
              <p className="section-kicker">Interpretation</p>
              <h2>Operational QA is not scientific review.</h2>
            </div>
            <div>
              <p>
                Model outputs are used to catch malformed packets, missing evidence,
                trace mismatches, and internal contradictions before publication.
                Agreement between models does not add independent scientific evidence.
              </p>
              <Link href="/methodology">Read the audit and human-approval boundary →</Link>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
