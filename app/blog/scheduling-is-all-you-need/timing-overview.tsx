import type { IntegerBoundaryManifest } from "./integer-boundary-galleries";
import styles from "./page.module.css";

type SweepFamily = IntegerBoundaryManifest["families"][number];
type SweepCase = SweepFamily["cases"][number];

const seriesColors = new Map([
  [4, "#5ce8ff"],
  [6, "#72e4ad"],
  [8, "#ffc66d"],
  [12, "#d59cff"],
]);

const chartBounds = {
  4: { minimum: 60, maximum: 190, ticks: [60, 90, 120, 150, 180] },
  8: { minimum: 60, maximum: 270, ticks: [60, 100, 140, 180, 220, 260] },
} as const;

function scheduleLabel(item: SweepCase) {
  if (item.sparse_nfe === 0) return `All dense · ${item.dense_nfe} steps`;
  if (item.dense_nfe === 0) return `All sparse · ${item.sparse_nfe} steps`;
  return `${item.sparse_nfe} sparse → ${item.dense_nfe} dense`;
}

function TimingChart({ family }: { family: SweepFamily }) {
  const width = 720;
  const height = 390;
  const margin = { top: 18, right: 24, bottom: 62, left: 66 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const bounds = chartBounds[family.turbo_profile as keyof typeof chartBounds];
  const x = (share: number) => margin.left + share * plotWidth;
  const y = (seconds: number) =>
    margin.top +
    ((bounds.maximum - seconds) / (bounds.maximum - bounds.minimum)) * plotHeight;
  const xTicks = [0, 0.25, 0.5, 0.75, 1];
  const chartTitleId = `timing-chart-${family.turbo_profile}-title`;
  const chartDescriptionId = `timing-chart-${family.turbo_profile}-description`;

  return (
    <article className={styles.timingChart}>
      <header>
        <div>
          <p>{family.case_count} measured sequences</p>
          <h3>Turbo {family.turbo_profile}-step</h3>
        </div>
        <div className={styles.timingLegend} aria-label="Total NFE line colors">
          {family.available_nfe.map((totalNfe) => (
            <span key={totalNfe}>
              <i style={{ backgroundColor: seriesColors.get(totalNfe) }} />
              {totalNfe} NFE
            </span>
          ))}
        </div>
      </header>

      <svg
        aria-labelledby={`${chartTitleId} ${chartDescriptionId}`}
        role="img"
        viewBox={`0 0 ${width} ${height}`}
      >
        <title id={chartTitleId}>
          {`Turbo ${family.turbo_profile}-step generation times`}
        </title>
        <desc id={chartDescriptionId}>
          Wall time in seconds by share of sparse attention. Lower points are faster. Each line
          represents one total-NFE budget.
        </desc>

        {bounds.ticks.map((tick) => (
          <g key={tick}>
            <line
              className={styles.timingChartGridline}
              x1={margin.left}
              x2={width - margin.right}
              y1={y(tick)}
              y2={y(tick)}
            />
            <text
              className={styles.timingChartTick}
              textAnchor="end"
              x={margin.left - 12}
              y={y(tick) + 4}
            >
              {tick}s
            </text>
          </g>
        ))}

        {xTicks.map((tick) => (
          <g key={tick}>
            <line
              className={styles.timingChartTickMark}
              x1={x(tick)}
              x2={x(tick)}
              y1={height - margin.bottom}
              y2={height - margin.bottom + 6}
            />
            <text
              className={styles.timingChartTick}
              textAnchor="middle"
              x={x(tick)}
              y={height - margin.bottom + 23}
            >
              {Math.round(tick * 100)}%
            </text>
          </g>
        ))}

        <line
          className={styles.timingChartAxis}
          x1={margin.left}
          x2={width - margin.right}
          y1={height - margin.bottom}
          y2={height - margin.bottom}
        />
        <line
          className={styles.timingChartAxis}
          x1={margin.left}
          x2={margin.left}
          y1={margin.top}
          y2={height - margin.bottom}
        />

        {family.available_nfe.map((totalNfe) => {
          const cases = family.cases.filter((item) => item.total_nfe === totalNfe);
          const color = seriesColors.get(totalNfe) ?? "#ffffff";
          const points = cases
            .map((item) => `${x(item.sparse_nfe / item.total_nfe)},${y(item.elapsed_seconds)}`)
            .join(" ");
          return (
            <g key={totalNfe}>
              <polyline
                fill="none"
                points={points}
                stroke={color}
                strokeLinejoin="round"
                strokeWidth="3"
                vectorEffect="non-scaling-stroke"
              />
              {cases.map((item) => (
                <circle
                  className={styles.timingChartPoint}
                  cx={x(item.sparse_nfe / item.total_nfe)}
                  cy={y(item.elapsed_seconds)}
                  fill={color}
                  key={item.id}
                  r="5"
                  stroke="#0a0e12"
                  strokeWidth="2"
                  vectorEffect="non-scaling-stroke"
                >
                  <title>
                    {`${totalNfe} NFE, ${scheduleLabel(item)}: ${item.elapsed_seconds.toFixed(1)} seconds`}
                  </title>
                </circle>
              ))}
            </g>
          );
        })}

        <text
          className={styles.timingChartAxisLabel}
          textAnchor="middle"
          x={margin.left + plotWidth / 2}
          y={height - 12}
        >
          SHARE OF EVALUATIONS USING SPARSE ATTENTION
        </text>
        <text
          className={styles.timingChartAxisLabel}
          textAnchor="middle"
          transform={`rotate(-90 16 ${margin.top + plotHeight / 2})`}
          x="16"
          y={margin.top + plotHeight / 2}
        >
          GENERATION TIME
        </text>
      </svg>
    </article>
  );
}

export function TimingOverview({ manifest }: { manifest: IntegerBoundaryManifest }) {
  return (
    <section className={styles.timingOverview} aria-labelledby="timing-overview-heading">
      <header className={styles.timingOverviewHeading}>
        <div>
          <p className={styles.kicker}>55-run timing overview</p>
          <h2 id="timing-overview-heading">Generation time at every handoff</h2>
        </div>
        <p>
          Each line moves from an all-dense schedule at 0% sparse to an all-sparse schedule at
          100%. Lower is faster. The panels use labeled but different vertical ranges so the
          shape of each Turbo family remains readable; the exact ledger below carries every
          measured value.
        </p>
      </header>

      <div className={styles.timingCharts}>
        {manifest.families.map((family) => (
          <TimingChart family={family} key={family.turbo_profile} />
        ))}
      </div>

      <div
        aria-label="Scrollable exact generation-time table"
        className={styles.timingTableWrap}
        tabIndex={0}
      >
        <table className={styles.timingTable}>
          <caption>Exact wall time for all 55 integer-boundary renders</caption>
          <thead>
            <tr>
              <th scope="col">Profile</th>
              <th scope="col">Total NFE</th>
              <th scope="col">Sparse → dense path</th>
              <th scope="col">Wall time</th>
              <th scope="col">Vs. dense</th>
              <th scope="col">Reduction</th>
            </tr>
          </thead>
          {manifest.families.flatMap((family) =>
            family.available_nfe.map((totalNfe) => {
              const cases = family.cases.filter((item) => item.total_nfe === totalNfe);
              const baseline = cases.find((item) => item.sparse_nfe === 0) ?? cases[0];
              return (
                <tbody key={`${family.turbo_profile}-${totalNfe}`}>
                  {cases.map((item, index) => {
                    const saved = baseline.elapsed_seconds - item.elapsed_seconds;
                    const reduction = (saved / baseline.elapsed_seconds) * 100;
                    const isBaseline = Math.abs(saved) < 0.05;
                    const isSlower = saved < -0.05;
                    return (
                      <tr data-case-id={item.id} key={item.id}>
                        {index === 0 ? (
                          <th rowSpan={cases.length} scope="rowgroup">
                            Turbo {family.turbo_profile}
                          </th>
                        ) : null}
                        {index === 0 ? (
                          <th rowSpan={cases.length} scope="rowgroup">
                            {totalNfe}
                          </th>
                        ) : null}
                        <td>{scheduleLabel(item)}</td>
                        <td><strong>{item.elapsed_seconds.toFixed(1)} s</strong></td>
                        <td className={isSlower ? styles.timingSlower : styles.timingSaved}>
                          {isBaseline
                            ? "baseline"
                            : isSlower
                              ? `${Math.abs(saved).toFixed(1)} s longer`
                              : `${saved.toFixed(1)} s saved`}
                        </td>
                        <td className={isSlower ? styles.timingSlower : styles.timingSaved}>
                          {isBaseline ? "—" : `${reduction.toFixed(1)}%`}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              );
            }),
          )}
        </table>
      </div>
    </section>
  );
}
