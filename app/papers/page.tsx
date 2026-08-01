import type { Metadata } from "next";
import Link from "next/link";
import { PaperCandidateQueue } from "@/components/paper-candidate-queue";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { StatusStrip } from "@/components/status-strip";
import { getLatestStudy } from "@/lib/study";

export const dynamic = "force-static";

export const metadata: Metadata = {
  title: "Candidate papers",
  description:
    "Review and vote on papers under consideration for independent computational replication by NULSPEC.",
  alternates: {
    canonical: "/papers",
  },
  openGraph: {
    title: "Candidate papers — NULSPEC",
    description:
      "Review and vote on papers under consideration for independent computational replication by NULSPEC.",
    url: "/papers",
  },
  twitter: {
    title: "Candidate papers — NULSPEC",
    description:
      "Review and vote on papers under consideration for independent computational replication by NULSPEC.",
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
              <h1>Candidate papers</h1>
              <p className="paper-queue-hero__lede">
                These papers are being considered for end-to-end computational
                replication. Votes help measure public interest; feasibility,
                available evidence, and research value determine which studies
                enter the replication workflow.
              </p>
              <Link className="paper-queue-hero__link" href="/#nominate">
                Nominate another paper →
              </Link>
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
                <dd>Interest informs, but does not determine, priority</dd>
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
