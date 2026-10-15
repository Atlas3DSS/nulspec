import type { Metadata } from "next";
import Link from "next/link";
import publicData from "@/site-data/random-acts/random-acts.public.json";
import { ActsDashboard, type ActsDoc } from "./acts-dashboard";
import styles from "./acts.module.css";

export const dynamic = "force-static";

const description =
  "Research code that is stuck on compute, run for free on our GPUs, with the measured result handed back.";

export const metadata: Metadata = {
  title: "Random acts of science",
  description,
  alternates: { canonical: "/acts/" },
  openGraph: { title: "Random acts of science", description, url: "/acts/" },
};

export default function ActsPage() {
  return (
    <>
      <header className={styles.banner}>
        <Link href="/" aria-label="NULSPEC home">NULSPEC</Link>
      </header>
      <main className={styles.page}>
        <ActsDashboard initial={publicData as ActsDoc} />
      </main>
    </>
  );
}
