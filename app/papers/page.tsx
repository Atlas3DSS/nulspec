import type { Metadata } from "next";
import Link from "next/link";
import { PaperCandidateQueue } from "@/components/paper-candidate-queue";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { StatusStrip } from "@/components/status-strip";
import { getLatestStudy } from "@/lib/study";

export const dynamic = "force-static";

export const metadata: Metadata = {
  title: "Paper nominations",
  description:
    "Review and vote on nominated papers. Votes record interest but do not determine NULSPEC eligibility, selection, protocols, or verdicts.",
  alternates: {
    canonical: "/papers",
  },
  openGraph: {
    title: "Paper nominations — NULSPEC",
    description:
      "Public-interest voting for nominated papers, separate from NULSPEC's documented selection methodology.",
    url: "/papers",
  },
  twitter: {
    title: "Paper nominations — NULSPEC",
    description:
      "Public-interest voting for nominated papers, separate from NULSPEC's documented selection methodology.",
  },
};

export default function CandidatePapersPage() {
  const study = getLatestStudy();

  return (
    <>
      <SiteHeader />
      <StatusStrip study={study} />
      <main id="main-content">
        <section className="paper-queue-hero">
          <div className="shell paper-queue-hero__grid">
            <div>
              <p className="hero__eyebrow">Replication candidates</p>
              <h1>Paper nominations</h1>
              <p className="paper-queue-hero__lede">
                These papers have been nominated for end-to-end computational
                replication. Votes measure public interest only. Objective
                eligibility, the published selection policy, and recorded
                priority or random allocation determine which studies start.
              </p>
              <div className="paper-queue-hero__links">
                <Link className="paper-queue-hero__link" href="/#nominate">
                  Nominate another paper →
                </Link>
                <Link className="paper-queue-hero__link" href="/selection">
                  Audit selection decisions →
                </Link>
              </div>
            </div>
            <dl className="paper-queue-hero__facts">
              <div>
                <dt>Default order</dt>
                <dd>Newest publication date</dd>
              </div>
              <div>
                <dt>Voting</dt>
                <dd>Anonymous, one vote per paper</dd>
              </div>
              <div>
                <dt>Selection</dt>
                <dd>Votes do not determine eligibility or selection</dd>
              </div>
            </dl>
          </div>
        </section>
        <PaperCandidateQueue />
      </main>
      <SiteFooter />
    </>
  );
}
