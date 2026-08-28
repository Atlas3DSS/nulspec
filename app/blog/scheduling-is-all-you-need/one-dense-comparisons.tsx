"use client";

import { useMemo, useRef, useState } from "react";
import type { IntegerBoundaryManifest } from "./integer-boundary-galleries";
import styles from "./page.module.css";

const postPath = "/blog/scheduling-is-all-you-need";
const assetPath = `${postPath}/integer-boundary-sweep`;

type SweepCase = IntegerBoundaryManifest["families"][number]["cases"][number];
type Pair = {
  dense: SweepCase;
  oneDense: SweepCase;
  totalNfe: number;
};
type Side = "dense" | "one-dense";

function caseLabel(item: SweepCase) {
  return item.sparse_nfe === 0
    ? `All dense · ${item.total_nfe} NFE`
    : `${item.sparse_nfe} sparse → 1 dense · ${item.total_nfe} NFE`;
}

export function OneDenseComparisons({ manifest }: { manifest: IntegerBoundaryManifest }) {
  const [profile, setProfile] = useState(4);
  const [selectedNfe, setSelectedNfe] = useState(4);
  const [mobileSide, setMobileSide] = useState<Side>("dense");
  const denseVideo = useRef<HTMLVideoElement>(null);
  const oneDenseVideo = useRef<HTMLVideoElement>(null);

  const profiles = useMemo(
    () => manifest.families.map((family) => family.turbo_profile),
    [manifest.families],
  );
  const family = manifest.families.find((candidate) => candidate.turbo_profile === profile);
  if (!family) throw new Error(`Missing Turbo ${profile} family`);

  const pairs = family.available_nfe.map<Pair>((totalNfe) => {
    const cases = family.cases.filter((item) => item.total_nfe === totalNfe);
    const dense = cases.find((item) => item.sparse_nfe === 0);
    const oneDense = cases.find((item) => item.dense_nfe === 1);
    if (!dense || !oneDense) throw new Error(`Missing one-dense pair for Turbo ${profile}/${totalNfe}`);
    return { dense, oneDense, totalNfe };
  });
  const pair = pairs.find((candidate) => candidate.totalNfe === selectedNfe) ?? pairs[0];
  const savedSeconds = pair.dense.elapsed_seconds - pair.oneDense.elapsed_seconds;
  const savedPercent = (savedSeconds / pair.dense.elapsed_seconds) * 100;

  function chooseProfile(nextProfile: number) {
    denseVideo.current?.pause();
    oneDenseVideo.current?.pause();
    setProfile(nextProfile);
    setSelectedNfe(4);
    setMobileSide("dense");
  }

  function chooseNfe(nextNfe: number) {
    denseVideo.current?.pause();
    oneDenseVideo.current?.pause();
    setSelectedNfe(nextNfe);
    setMobileSide("dense");
  }

  function chooseMobileSide(side: Side) {
    denseVideo.current?.pause();
    oneDenseVideo.current?.pause();
    setMobileSide(side);
  }

  return (
    <section className={styles.focusPairs} aria-labelledby="one-dense-heading">
      <header className={styles.focusPairsHeading}>
        <div>
          <p className={styles.kicker}>Focused A/B comparison</p>
          <h2 id="one-dense-heading">What one final dense step changes</h2>
        </div>
        <p>
          Match every all-dense control against the schedule that keeps all but its final
          evaluation sparse. Start either player independently; starting one automatically
          pauses the other so their audio never overlaps.
        </p>
      </header>

      <div className={styles.focusPairControls}>
        <div aria-label="Turbo family" className={styles.focusPairTabs}>
          {profiles.map((candidate) => (
            <button
              aria-pressed={profile === candidate}
              key={candidate}
              onClick={() => chooseProfile(candidate)}
              type="button"
            >
              Turbo {candidate}
            </button>
          ))}
        </div>
        <div aria-label="Total NFE" className={styles.focusPairTabs}>
          {pairs.map((candidate) => (
            <button
              aria-pressed={selectedNfe === candidate.totalNfe}
              key={candidate.totalNfe}
              onClick={() => chooseNfe(candidate.totalNfe)}
              type="button"
            >
              {candidate.totalNfe} NFE
            </button>
          ))}
        </div>
      </div>

      <div className={styles.focusMobileSwitch} aria-label="Visible comparison side">
        <button
          aria-pressed={mobileSide === "dense"}
          onClick={() => chooseMobileSide("dense")}
          type="button"
        >
          A · All dense
        </button>
        <button
          aria-pressed={mobileSide === "one-dense"}
          onClick={() => chooseMobileSide("one-dense")}
          type="button"
        >
          B · Sparse → dense
        </button>
      </div>

      <div className={styles.focusPairStage} aria-live="polite">
        <article
          className={`${styles.focusPairCard} ${
            mobileSide !== "dense" ? styles.focusPairCardMobileHidden : ""
          }`}
        >
          <video
            controls
            key={pair.dense.id}
            onPlay={() => oneDenseVideo.current?.pause()}
            playsInline
            preload="metadata"
            ref={denseVideo}
            src={`${assetPath}/${pair.dense.file}`}
          />
          <div>
            <p>A · Dense control</p>
            <h3>{caseLabel(pair.dense)}</h3>
            <strong>{pair.dense.elapsed_seconds.toFixed(1)} s</strong>
            <span>generation time</span>
          </div>
        </article>

        <article
          className={`${styles.focusPairCard} ${styles.focusPairCardOneDense} ${
            mobileSide !== "one-dense" ? styles.focusPairCardMobileHidden : ""
          }`}
        >
          <video
            controls
            key={pair.oneDense.id}
            onPlay={() => denseVideo.current?.pause()}
            playsInline
            preload="metadata"
            ref={oneDenseVideo}
            src={`${assetPath}/${pair.oneDense.file}`}
          />
          <div>
            <p>B · One dense finish</p>
            <h3>{caseLabel(pair.oneDense)}</h3>
            <strong>{pair.oneDense.elapsed_seconds.toFixed(1)} s</strong>
            <span>generation time</span>
          </div>
        </article>
      </div>

      <footer className={styles.focusPairResult}>
        <strong>{savedSeconds.toFixed(1)} s saved</strong>
        <span>{savedPercent.toFixed(1)}% faster than the matched all-dense control</span>
      </footer>
    </section>
  );
}
