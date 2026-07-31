import Link from "next/link";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

export default function NotFound() {
  return (
    <>
      <SiteHeader />
      <main id="main-content" className="not-found shell">
        <p className="section-kicker">404 · Page not found</p>
        <h1>This page does not exist.</h1>
        <p>The requested URL does not match a published NULSPEC page or artifact.</p>
        <Link className="button button--primary" href="/">
          Return to the home page
        </Link>
      </main>
      <SiteFooter />
    </>
  );
}
