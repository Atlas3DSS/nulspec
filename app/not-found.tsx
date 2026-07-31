import Link from "next/link";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

export default function NotFound() {
  return (
    <>
      <SiteHeader />
      <main id="main-content" className="not-found shell">
        <p className="section-kicker">404 · Null reference</p>
        <h1>This artifact does not exist.</h1>
        <p>No missing result has been silently imputed.</p>
        <Link className="button button--primary" href="/">
          Return to the ledger
        </Link>
      </main>
      <SiteFooter />
    </>
  );
}
