import Link from "next/link";

export default function NotFound() {
  return (
    <main className="not-found">
      <Link className="not-found__brand" href="/">NULSPEC</Link>
      <p className="eyebrow">404</p>
      <h1>Nothing here.</h1>
      <Link className="not-found__link" href="/">Return home</Link>
    </main>
  );
}
