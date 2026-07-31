import Link from "next/link";
import { NulspecMark } from "@/components/nulspec-mark";
import { getLatestStudy } from "@/lib/study";

export function SiteHeader() {
  const study = getLatestStudy();
  return (
    <header className="site-header">
      <div className="shell site-header__inner">
        <Link className="wordmark" href="/" aria-label="NULSPEC home">
          <NulspecMark className="wordmark__mark" />
          <span>NUL</span>
          <span className="wordmark__accent">SPEC</span>
        </Link>
        <nav aria-label="Primary navigation">
          <ul className="site-nav">
            <li>
              <Link href={`/studies/${study.study_id}`}>Study {study.study_id}</Link>
            </li>
            <li>
              <Link href="/#method">Method</Link>
            </li>
            <li>
              <Link href="/#about">About</Link>
            </li>
          </ul>
        </nav>
      </div>
    </header>
  );
}
