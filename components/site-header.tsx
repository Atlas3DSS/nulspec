import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="site-header">
      <div className="shell site-header__inner">
        <Link className="wordmark" href="/" aria-label="NULSPEC home">
          <span>NUL</span>
          <span className="wordmark__accent">SPEC</span>
          <span className="wordmark__null" aria-hidden="true">
            ∅
          </span>
        </Link>
        <nav aria-label="Primary navigation">
          <ul className="site-nav">
            <li>
              <Link href="/studies/001">Study 001</Link>
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
