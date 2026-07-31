import Link from "next/link";
import { NulspecMark } from "@/components/nulspec-mark";
import { GITHUB_URL, KOFI_URL, NOMINATE_URL } from "@/lib/study";

export function SiteFooter() {
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
              Null results. Executable specifications.
            </p>
          </div>
          <div className="footer-actions">
            <a href={NOMINATE_URL}>Nominate a paper ↗</a>
            <a href={KOFI_URL}>Fund GPU-hours ↗</a>
            <a href={GITHUB_URL}>GitHub ↗</a>
          </div>
        </div>
        <div className="site-footer__bottom">
          <p>
            A small team of enthusiasts and accelerationalists, checking
            the work on hardware we control.
          </p>
          <Link href="/studies/001">Study 001 is running</Link>
        </div>
      </div>
    </footer>
  );
}
