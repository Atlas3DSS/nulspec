import Image from "next/image";
import Link from "next/link";

const postPath = "/blog/scheduling-is-all-you-need/";

export function SiteHome() {
  return (
    <>
      <header className="site-banner">
        <Link href="/" aria-label="NULSPEC home">NULSPEC</Link>
      </header>
      <main className="home">
        <section className="home__intro">
          <p className="eyebrow">Independent / experimental</p>
          <h1>AI enthusiasts doing things.</h1>
          <p>
            We build, test, compare, and write down the parts worth sharing.
          </p>
        </section>

        <section className="home__latest" aria-labelledby="latest-heading">
          <p className="eyebrow" id="latest-heading">Latest</p>
          <Link className="post-card" href={postPath}>
            <span className="post-card__image">
              <Image
                src={`${postPath}h3-sparsity-timing.svg`}
                alt="Bar chart comparing wall time across dense and sparse H3 sampling schedules"
                width={1200}
                height={630}
                unoptimized
              />
            </span>
            <span className="post-card__body">
              <span className="post-card__meta">H3 / inference</span>
              <strong>
                Scheduling is all you need: use sparsity to save time while controlling loss.
              </strong>
              <span className="post-card__summary">
                Six fixed-seed sequences show what different sparse and dense attention
                schedules cost in wall time. The outputs are presented together for direct
                comparison.
              </span>
              <span className="post-card__link">Read and watch <span aria-hidden="true">↗</span></span>
            </span>
          </Link>
        </section>
      </main>
    </>
  );
}
