import Link from "next/link";
import { NulspecMark } from "@/components/nulspec-mark";
import { GITHUB_URL, KOFI_URL, NOMINATE_URL, getLatestStudy } from "@/lib/study";

export function SiteFooter() {
  const study = getLatestStudy();
  return (
    <footer className="site-footer">
      <div className="shell">
        <div className="site-footer__top">
          <div>
            <p className="wordmark wordmark--footer" aria-label="NULSPEC">
              <NulspecMark className="wordmark__mark" />
              <span>NUL</span>
              <span className="wordmark__accent">SPEC</span>
            </p>
            <p className="site-footer__line">
              Independent replication of published research.
            </p>
          </div>
          <div className="footer-actions">
            <Link href="/methodology">Methodology</Link>
            <Link href="/selection">Selection ledger</Link>
            <Link href="/papers">Paper nominations</Link>
            <Link href="/operations">Operations ledger</Link>
            <a href={NOMINATE_URL}>Nominate a paper ↗</a>
            <a href={KOFI_URL}>Support replication work ↗</a>
            <a href={GITHUB_URL}>GitHub ↗</a>
          </div>
        </div>
        <div className="site-footer__bottom">
          <p>
            NULSPEC is focused on independent replication of computational
            machine-learning claims using team-operated compute.
          </p>
          <Link href={`/studies/${study.study_id}`}>
            View Study {study.study_id}
          </Link>
        </div>
      </div>
    </footer>
  );
}
