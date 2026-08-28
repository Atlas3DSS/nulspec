"use client";

import { useMemo, useState } from "react";
import styles from "./page.module.css";

const postPath = "/blog/scheduling-is-all-you-need";
const assetPath = `${postPath}/integer-boundary-sweep`;
const pageSize = 3;

type SweepCase = {
  id: string;
  turbo_profile: number;
  total_nfe: number;
  sparse_nfe: number;
  dense_nfe: number;
  handoff_after_step: number | null;
  endpoint: "all_dense" | "all_sparse" | null;
  elapsed_seconds: number;
  file: string;
  bytes: number;
  sha256: string;
};

type SweepFamily = {
  turbo_profile: number;
  name: string;
  available_nfe: number[];
  case_count: number;
  cases: SweepCase[];
};

export type IntegerBoundaryManifest = {
  schema: "nulspec_h3_integer_boundary_gallery_v1";
  case_count: number;
  families: SweepFamily[];
};

function pathLabel(item: SweepCase) {
  if (item.endpoint === "all_dense") return `All dense · ${item.dense_nfe} steps`;
  if (item.endpoint === "all_sparse") return `All sparse · ${item.sparse_nfe} steps`;
  return `Sparse ${item.sparse_nfe} → dense ${item.dense_nfe}`;
}

function SweepCard({ item, baseline }: { item: SweepCase; baseline: SweepCase }) {
  const returned = baseline.elapsed_seconds - item.elapsed_seconds;
  const percentage = Math.abs((returned / baseline.elapsed_seconds) * 100);
  const timing =
    Math.abs(returned) < 0.05
      ? "dense timing baseline"
      : returned > 0
        ? `${returned.toFixed(1)} s saved · ${percentage.toFixed(1)}%`
        : `${Math.abs(returned).toFixed(1)} s longer · ${percentage.toFixed(1)}%`;

  return (
    <article className={styles.sweepCard}>
      <video
        className={styles.sweepVideo}
        controls
        playsInline
        preload="metadata"
        src={`${assetPath}/${item.file}`}
      />
      <div className={styles.sweepCardBody}>
        <div className={styles.sweepCardHeading}>
          <div>
            <p>{item.total_nfe} total NFE</p>
            <h4>{pathLabel(item)}</h4>
          </div>
          <strong>{item.elapsed_seconds.toFixed(1)} s</strong>
        </div>
        <div className={styles.sweepSplit}>
          {item.sparse_nfe > 0 ? (
            <span className={styles.sparsePhase} style={{ flexGrow: item.sparse_nfe }}>
              {item.sparse_nfe} sparse
            </span>
          ) : null}
          {item.dense_nfe > 0 ? (
            <span className={styles.densePhase} style={{ flexGrow: item.dense_nfe }}>
              {item.dense_nfe} dense
            </span>
          ) : null}
        </div>
        <p className={returned > 0.05 ? styles.sweepSaved : styles.sweepDelta}>
          {timing}
        </p>
      </div>
    </article>
  );
}

function SweepFamilyGallery({ family }: { family: SweepFamily }) {
  const [selectedNfe, setSelectedNfe] = useState(family.available_nfe[0]);
  const [page, setPage] = useState(0);
  const filteredCases = useMemo(
    () => family.cases.filter((item) => item.total_nfe === selectedNfe),
    [family.cases, selectedNfe],
  );
  const pageCount = Math.ceil(filteredCases.length / pageSize);
  const visibleCases = filteredCases.slice(page * pageSize, (page + 1) * pageSize);
  const baseline = filteredCases.find((item) => item.sparse_nfe === 0) ?? filteredCases[0];
  const familyId = `sweep-turbo-${family.turbo_profile}`;

  function chooseNfe(nfe: number) {
    setSelectedNfe(nfe);
    setPage(0);
  }

  return (
    <section className={styles.sweepFamily} aria-labelledby={familyId}>
      <header className={styles.sweepFamilyHeading}>
        <div>
          <p className={styles.kicker}>{family.case_count} sequences</p>
          <h3 id={familyId}>{family.turbo_profile}-step Turbo gallery</h3>
        </div>
        <div className={styles.nfeTabs} role="tablist" aria-label={`${family.name} total NFE`}>
          {family.available_nfe.map((nfe) => (
            <button
              aria-selected={selectedNfe === nfe}
              className={selectedNfe === nfe ? styles.nfeTabActive : styles.nfeTab}
              key={nfe}
              onClick={() => chooseNfe(nfe)}
              role="tab"
              type="button"
            >
              {nfe} NFE
            </button>
          ))}
        </div>
      </header>

      <div className={styles.sweepGrid} aria-live="polite">
        {visibleCases.map((item) => (
          <SweepCard baseline={baseline} item={item} key={item.id} />
        ))}
      </div>

      <nav className={styles.sweepPager} aria-label={`${family.name} gallery pages`}>
        <button disabled={page === 0} onClick={() => setPage(page - 1)} type="button">
          ← Previous three
        </button>
        <div className={styles.sweepPageNumbers}>
          {Array.from({ length: pageCount }, (_, index) => (
            <button
              aria-current={page === index ? "page" : undefined}
              key={index}
              onClick={() => setPage(index)}
              type="button"
            >
              {index + 1}
            </button>
          ))}
        </div>
        <button
          disabled={page === pageCount - 1}
          onClick={() => setPage(page + 1)}
          type="button"
        >
          Next three →
        </button>
      </nav>
      <p className={styles.sweepPosition}>
        Showing {page * pageSize + 1}–{page * pageSize + visibleCases.length} of{" "}
        {filteredCases.length} schedules at {selectedNfe} total NFE
      </p>
    </section>
  );
}

export function IntegerBoundaryGalleries({ manifest }: { manifest: IntegerBoundaryManifest }) {
  return (
    <section className={styles.sweep} aria-labelledby="integer-boundary-sweep-heading">
      <header className={styles.sweepHeading}>
        <p className={styles.kicker}>55-render addendum</p>
        <h2 id="integer-boundary-sweep-heading">Every integer handoff, three at a time</h2>
        <p>
          Choose the four- or eight-step Turbo family, select a total NFE budget, then move
          through each sparse-to-dense boundary in sets of three. Every sequence keeps the same
          first frame, prompt, seed, base checkpoint, Euler sampler, Simple schedule, and
          continuous latent. The sparse stage uses a 30% video-KV budget; the dense stage uses
          Comfy Kitchen INT8.
        </p>
      </header>
      <div className={styles.sweepFamilies}>
        {manifest.families.map((family) => (
          <SweepFamilyGallery family={family} key={family.turbo_profile} />
        ))}
      </div>
    </section>
  );
}
