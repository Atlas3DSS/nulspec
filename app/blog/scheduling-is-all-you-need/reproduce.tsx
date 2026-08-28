import Image from "next/image";
import styles from "./page.module.css";

const postPath = "/blog/scheduling-is-all-you-need";
const repository = "https://github.com/Zironic/H3-Optimizations";

const charts = [
  {
    family: "Turbo 4-step",
    file: "h3-turbo4-time-equivalence.png",
    width: 2539,
    height: 1713,
    alt: "Turbo 4 time-equivalence chart comparing six fully dense evaluations with eight evaluations split into seven sparse and one dense step",
  },
  {
    family: "Turbo 8-step",
    file: "h3-turbo8-time-equivalence.png",
    width: 2576,
    height: 1713,
    alt: "Turbo 8 time-equivalence chart comparing eight fully dense evaluations with twelve evaluations split into eleven sparse and one dense step",
  },
];

export function ReproduceStudy() {
  return (
    <section className={styles.reproduce} aria-labelledby="reproduce-heading">
      <header className={styles.reproduceHeading}>
        <div>
          <p className={styles.kicker}>Time-equivalent depth</p>
          <h2 id="reproduce-heading">Spend sparsity on more denoising</h2>
        </div>
        <p>
          These two views isolate the practical exchange: a longer schedule can fit inside—or
          very near—the wall-time envelope of a shorter fully dense run when most early
          evaluations are sparse and the final evaluation is dense.
        </p>
      </header>

      <div className={styles.equivalenceCharts}>
        {charts.map((chart) => (
          <figure key={chart.file}>
            <Image
              alt={chart.alt}
              height={chart.height}
              src={`${postPath}/${chart.file}`}
              unoptimized
              width={chart.width}
            />
            <figcaption>{chart.family} · measured RTX 6000 Pro S wall time</figcaption>
          </figure>
        ))}
      </div>

      <div className={styles.replicationCard}>
        <div className={styles.replicationLead}>
          <p className={styles.kicker}>ComfyUI replication kit</p>
          <h3>One custom sampler. Everything around it stays stock.</h3>
          <p>
            H3-Optimizations 0.3.0 adds the exact integer-boundary sampler used here and no new
            Python dependencies. Import the workflow matching the Turbo adapter, choose the
            total schedule length in <code>BasicScheduler</code>, then set the sampler&apos;s sparse
            step count. The remaining evaluations are dense automatically.
          </p>
        </div>

        <dl className={styles.replicationContract}>
          <div><dt>Sampler / scheduler</dt><dd>Euler / Simple</dd></div>
          <div><dt>Sparse attention</dt><dd>Kitchen INT8 · 30% video KV</dd></div>
          <div><dt>Handoff</dt><dd>Same latent and sigmas · no fresh noise</dd></div>
          <div><dt>Dense finish</dt><dd>Comfy Kitchen INT8</dd></div>
        </dl>

        <nav className={styles.replicationLinks} aria-label="H3 replication downloads">
          <a href={repository}>GitHub project</a>
          <a href={`${repository}/archive/refs/tags/v0.3.0.zip`}>Download v0.3.0</a>
          <a href={`${repository}/blob/main/workflows/h3_sparse_dense_exact_turbo4.json`}>
            Turbo 4 workflow
          </a>
          <a href={`${repository}/blob/main/workflows/h3_sparse_dense_exact_turbo8.json`}>
            Turbo 8 workflow
          </a>
        </nav>
      </div>
    </section>
  );
}
