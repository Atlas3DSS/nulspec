import type { Metadata } from "next";
import Link from "next/link";
import integerBoundaryManifest from "@/public/blog/scheduling-is-all-you-need/integer-boundary-sweep/manifest.json";
import {
  IntegerBoundaryGalleries,
  type IntegerBoundaryManifest,
} from "./integer-boundary-galleries";
import { CompareToggle, ComparisonProvider } from "./comparison";
import { OneDenseComparisons } from "./one-dense-comparisons";
import { TimingOverview } from "./timing-overview";
import styles from "./page.module.css";

const postPath = "/blog/scheduling-is-all-you-need";
const title = "Scheduling is all you need: use sparsity to save time while controlling loss.";

export const metadata: Metadata = {
  title,
  description:
    "Six headline MiniMax H3 sequences and a 55-render integer handoff sweep compare dense, sparse, and sparse-to-dense attention schedules by measured wall time.",
  alternates: {
    canonical: `${postPath}/`,
  },
  openGraph: {
    type: "article",
    title,
    description:
      "Six headline H3 sequences, a 55-render integer handoff sweep, and the wall time returned by different attention schedules.",
    url: `${postPath}/`,
    publishedTime: "2026-08-28T00:00:00Z",
    images: [
      {
        url: `${postPath}/h3-sparsity-timing.svg`,
        width: 1200,
        height: 630,
        alt: "H3 wall-time comparison across dense and sparse sampling schedules",
      },
    ],
  },
};

type BatteryCase = {
  id: string;
  name: string;
  family: "4-step" | "8-step";
  nfe: number;
  elapsed: number;
  baseline: number;
  turbo: string;
  shifts: string;
  attention: string;
  schedule: string;
  narrative: string;
  file: string;
};

const cases: BatteryCase[] = [
  {
    id: "current_sage_4",
    name: "Dense 4 · SageAttention",
    family: "4-step",
    nfe: 4,
    elapsed: 99.76,
    baseline: 99.76,
    turbo: "H3 Turbo 4-step",
    shifts: "6 / 3",
    attention: "SageAttention × 4",
    schedule: "One complete 4-step sigma schedule",
    narrative:
      "The dense four-step sequence completed in 99.8 seconds. It is the timing baseline for the other four-step schedules.",
    file: "current_sage_4_00001_.mp4",
  },
  {
    id: "sparse2_dense2_4nfe",
    name: "Sparse 2 → dense 2",
    family: "4-step",
    nfe: 4,
    elapsed: 75.236,
    baseline: 99.76,
    turbo: "H3 Turbo 4-step",
    shifts: "6 / 3",
    attention: "Sparse Kitchen at 30% video KV × 2 → SageAttention × 2",
    schedule: "One complete 4-step sigma schedule; handoff at midpoint",
    narrative:
      "Making the first half sparse while keeping four total evaluations reduced wall time to 75.2 seconds—a saving of 24.5 seconds, or 24.6%.",
    file: "sparse2_dense2_4nfe_00001_.mp4",
  },
  {
    id: "sparse2_dense4_6nfe",
    name: "Sparse 2 → dense 4",
    family: "4-step",
    nfe: 6,
    elapsed: 94.744,
    baseline: 99.76,
    turbo: "H3 Turbo 4-step",
    shifts: "6 / 3",
    attention: "Sparse Kitchen at 30% video KV × 2 → SageAttention × 4",
    schedule: "Four-step trajectory; final half subdivided into 4 dense evaluations",
    narrative:
      "Spending four dense evaluations over the final half completed in 94.7 seconds. That saved 5.0 seconds, or 5.0%, against the dense four-step baseline while using six evaluations.",
    file: "sparse2_dense4_6nfe_00001_.mp4",
  },
  {
    id: "current_sage_8",
    name: "Dense 8 · SageAttention",
    family: "8-step",
    nfe: 8,
    elapsed: 184.311,
    baseline: 184.311,
    turbo: "H3 Turbo 8-step",
    shifts: "12 / 3",
    attention: "SageAttention × 8",
    schedule: "One complete 8-step sigma schedule",
    narrative:
      "The dense eight-step sequence completed in 184.3 seconds. It is the timing baseline for the other eight-step schedules.",
    file: "current_sage_8_00001_.mp4",
  },
  {
    id: "all_sparse_8",
    name: "All sparse 8",
    family: "8-step",
    nfe: 8,
    elapsed: 126.759,
    baseline: 184.311,
    turbo: "H3 Turbo 8-step",
    shifts: "12 / 3",
    attention: "Sparse Kitchen at 30% video KV × 8",
    schedule: "One complete 8-step sigma schedule; no stage handoff",
    narrative:
      "Keeping all eight evaluations sparse completed in 126.8 seconds. That saved 57.6 seconds, or 31.2%, against the dense eight-step baseline.",
    file: "all_sparse_8_00001_.mp4",
  },
  {
    id: "sparse4_dense4_8nfe",
    name: "Sparse 4 → dense 4",
    family: "8-step",
    nfe: 8,
    elapsed: 149.117,
    baseline: 184.311,
    turbo: "H3 Turbo 8-step",
    shifts: "12 / 3",
    attention: "Sparse Kitchen at 30% video KV × 4 → SageAttention × 4",
    schedule: "One complete 8-step sigma schedule; handoff at midpoint",
    narrative:
      "Changing from sparse to dense attention at the midpoint completed in 149.1 seconds. That saved 35.2 seconds, or 19.1%, against the dense eight-step baseline.",
    file: "sparse4_dense4_8nfe_00001_.mp4",
  },
];

const fixedPrompt = `integrated_multimodal_description:
<Picture 1> is the exact first frame. Preserve the exact on-screen subject visible in this image, including its identity, species-defining anatomy, head and facial structure, surface covering, proportions, clothing, background, framing, and lighting. Do not humanize the subject or change its species. [Shot 1] One continuous, natural medium close-up with a locked camera. The subject looks directly into the camera, blinks naturally, makes small restrained head and hand movements, and speaks clearly with calm confidence. Keep the subject's face stable and mouth movement precisely synchronized. (S1), the on-screen subject, says: <d>[English] Atlas began with a simple idea: creative tools should work together instead of getting in the way. We connected the first pieces, tested them on real projects, and kept refining them until Atlas became a practical creative partner.</d> The subject finishes the sentence, closes its mouth naturally, and holds eye contact for the final moment. No cuts, no camera movement, no captions, no subtitles, no logos, and no visible text.
overall_soundscape:
Clean close-miked speech from (S1), subtle natural room tone, quiet breathing, and faint clothing movement. No other voices or prominent environmental sounds.
non_diegetic_music:
N/A`;

function CaseCard({ item }: { item: BatteryCase }) {
  const improvement = 100 * (1 - item.elapsed / item.baseline);
  const saved = item.baseline - item.elapsed;
  const isBaseline = saved < 0.01;

  return (
    <article className={styles.card}>
      <video
        className={styles.video}
        controls
        playsInline
        preload="metadata"
        src={`${postPath}/${item.file}`}
      />
      <CompareToggle
        item={{
          id: `headline:${item.id}`,
          title: item.name,
          context: `${item.turbo} · ${item.nfe} NFE`,
          runtime: `${item.elapsed.toFixed(1)} s`,
          video: `${postPath}/${item.file}`,
        }}
      />
      <div className={styles.cardBody}>
        <div className={styles.cardTop}>
          <div>
            <p>{item.family} family</p>
            <h3>{item.name}</h3>
          </div>
          <span>{item.nfe} NFE</span>
        </div>

        <div className={styles.runtime}>
          <strong>{item.elapsed.toFixed(1)} s</strong>
          <span className={isBaseline ? styles.baseline : styles.faster}>
            {isBaseline
              ? "timing baseline"
              : `${saved.toFixed(1)} s saved · ${improvement.toFixed(1)}%`}
          </span>
        </div>
        <div className={styles.bar} aria-hidden="true">
          <span style={{ width: `${(item.elapsed / 184.311) * 100}%` }} />
        </div>

        <dl className={styles.sampling}>
          <div><dt>Adapter</dt><dd>{item.turbo}</dd></div>
          <div><dt>Sampler / scheduler</dt><dd>Euler / Simple</dd></div>
          <div><dt>Shifts</dt><dd>{item.shifts}</dd></div>
          <div><dt>Attention path</dt><dd>{item.attention}</dd></div>
          <div><dt>Noise schedule</dt><dd>{item.schedule}</dd></div>
        </dl>

        <p className={styles.narrative}>{item.narrative}</p>
      </div>
    </article>
  );
}

function Family({ family }: { family: BatteryCase["family"] }) {
  const familyCases = cases.filter((item) => item.family === family);

  return (
    <section className={styles.family} aria-labelledby={`family-${family}`}>
      <div className={styles.familyHeading}>
        <div>
          <p className={styles.kicker}>{family === "4-step" ? "01" : "02"} / {family} family</p>
          <h2 id={`family-${family}`}>
            {family === "4-step" ? "Four-step trajectory" : "Eight-step trajectory"}
          </h2>
        </div>
        <p>
          {family === "4-step"
            ? "The dense and 2→2 paths use four evaluations. The 2→4 path adds dense subdivisions across the trajectory's final half for six evaluations total."
            : "All three paths use the same eight-step Turbo adapter, shifts, sampler, scheduler, and complete sigma schedule. The attention path is the changing variable."}
        </p>
      </div>
      <div className={styles.grid}>
        {familyCases.map((item) => <CaseCard item={item} key={item.id} />)}
      </div>
    </section>
  );
}

export default function H3SamplerPaths() {
  return (
    <ComparisonProvider>
      <header className={styles.siteBanner}>
        <Link href="/">NULSPEC</Link>
      </header>
      <main className={styles.page}>
        <header className={styles.hero}>
          <div className={styles.shell}>
            <p className={styles.kicker}>H3 inference / schedule comparison</p>
            <h1>{title}</h1>
            <p className={styles.lede}>
              Six MiniMax H3 execution paths receive the same first frame, prompt, seed,
              checkpoint, resolution, and duration. The Turbo profile and attention schedule
              change; measured wall time is reported for every sequence. A complete 55-render
              integer handoff sweep follows at the bottom.
            </p>
            <dl className={styles.facts}>
              <div><dt>Sequences</dt><dd>6 + 55 sweep</dd></div>
              <div><dt>Seed</dt><dd>260827104729</dd></div>
              <div><dt>Format</dt><dd>768² · 15.08 s</dd></div>
              <div><dt>Base</dt><dd>MiniMax H3 FL2VA</dd></div>
            </dl>
          </div>
        </header>

        <div className={styles.shell}>
          <div className={styles.articleLayout}>
            <aside className={styles.method} aria-labelledby="fixed-setup-heading">
              <p className={styles.kicker}>Fixed setup</p>
              <div>
                <h2 id="fixed-setup-heading">One first frame, prompt, seed, and base checkpoint</h2>
                <p>
                  Every sequence renders a requested 15-second clip at 768×768 with Euler and
                  Simple, fixed seed 260827104729, the same supplied first frame, the exact prompt
                  reproduced below, and no user LoRAs. The four- and eight-step groups use their
                  matching H3 Turbo adapters and shift profiles.
                </p>
                <p>
                  All six files contain H.264 video at 24 fps and stereo AAC audio at 32 kHz.
                  The output duration is 15.08 seconds in every case.
                </p>
              </div>
            </aside>

            <div className={styles.comparisons}>
              <Family family="4-step" />
              <Family family="8-step" />
            </div>

            <aside className={styles.timing} aria-labelledby="wall-time-heading">
              <p className={styles.kicker}>Wall-time result</p>
              <div>
                <h2 id="wall-time-heading">What each sparse sequence returned to the clock</h2>
                <p>
                  In the four-step family, sparse 2 → dense 2 reduced the dense baseline from
                  99.8 to 75.2 seconds, returning 24.5 seconds. Sparse 2 → dense 4 completed in
                  94.7 seconds, returning 5.0 seconds while spending two additional evaluations
                  over the final half.
                </p>
                <p>
                  In the eight-step family, all-sparse attention reduced the dense baseline from
                  184.3 to 126.8 seconds, returning 57.6 seconds. The sparse 4 → dense 4 midpoint
                  handoff completed in 149.1 seconds, returning 35.2 seconds.
                </p>
              </div>
            </aside>
          </div>

          <details className={styles.prompt}>
            <summary>Exact fixed prompt</summary>
            <pre>{fixedPrompt}</pre>
          </details>

          <TimingOverview
            manifest={integerBoundaryManifest as unknown as IntegerBoundaryManifest}
          />

          <OneDenseComparisons
            manifest={integerBoundaryManifest as unknown as IntegerBoundaryManifest}
          />

          <IntegerBoundaryGalleries
            manifest={integerBoundaryManifest as unknown as IntegerBoundaryManifest}
          />
        </div>
      </main>
    </ComparisonProvider>
  );
}
