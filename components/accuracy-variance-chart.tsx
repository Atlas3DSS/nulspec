import {
  armEvidenceUrl,
  type AccuracyMetricSummary,
  type AccuracyStudyDocument,
} from "@/lib/study";

const series = [
  { key: "exact_public_sprkd", label: "SPRKD · exact public path" },
  { key: "paper_intent_sprkd", label: "SPRKD · paper-intent path" },
  { key: "control_student", label: "Control-S" },
  { key: "paper_intent_response_kd", label: "Response KD · paper intent" },
] as const;

const domain = { minimum: 45, maximum: 100 };

function position(value: number) {
  const clamped = Math.min(domain.maximum, Math.max(domain.minimum, value));
  return ((clamped - domain.minimum) / (domain.maximum - domain.minimum)) * 100;
}

function percent(value: number) {
  return `${value.toFixed(3)}%`;
}

function interval(metric: AccuracyMetricSummary) {
  const [low, high] = metric.observed.descriptive_t95_interval;
  return `${percent(low)} to ${percent(high)}`;
}

export function AccuracyVarianceChart({
  study,
}: {
  study: AccuracyStudyDocument;
}) {
  return (
    <figure className="accuracy-variance">
      <div className="accuracy-variance__header">
        <div>
          <p className="section-kicker">Final accuracy across frozen seeds</p>
          <h3>Training-seed variability</h3>
        </div>
        <div className="accuracy-variance__legend" aria-hidden="true">
          <span><i className="is-seed" />Seed</span>
          <span><i className="is-mean" />Mean</span>
          <span><i className="is-reported" />Paper mean</span>
        </div>
      </div>

      <div className="accuracy-variance__axis" aria-hidden="true">
        {[50, 60, 70, 80, 90, 100].map((tick) => (
          <span key={tick} style={{ left: `${position(tick)}%` }}>{tick}%</span>
        ))}
      </div>

      <div className="accuracy-variance__rows">
        {series.map(({ key, label }) => {
          const metric = study.primary.metrics[key];
          if (!metric) return null;
          const observed = metric.observed;
          const [low, high] = observed.descriptive_t95_interval;
          const whiskerLeft = position(low);
          const whiskerRight = position(high);
          const description =
            `${label}. Mean ${percent(observed.mean)}. Sample standard deviation ` +
            `${percent(observed.sample_sd)}. Descriptive 95 percent Student t interval ` +
            `${interval(metric)}. Seed values ${observed.per_seed
              .map((value) => percent(value))
              .join(", ")}.`;

          return (
            <div className="accuracy-variance__row" key={key}>
              <div className="accuracy-variance__label">
                <strong>{label}</strong>
                <span>
                  mean {percent(observed.mean)} · SD {percent(observed.sample_sd)}
                </span>
              </div>
              <div
                aria-label={description}
                className="accuracy-variance__plot"
                role="group"
              >
                <span className="accuracy-variance__grid" aria-hidden="true" />
                <span
                  className="accuracy-variance__interval"
                  style={{
                    left: `${whiskerLeft}%`,
                    width: `${Math.max(whiskerRight - whiskerLeft, 0.8)}%`,
                  }}
                  title={`Descriptive t interval: ${interval(metric)}`}
                />
                {metric.reported_accuracy !== undefined ? (
                  <span
                    className="accuracy-variance__reported"
                    style={{ left: `${position(metric.reported_accuracy)}%` }}
                    title={`Paper mean ${percent(metric.reported_accuracy)}`}
                  />
                ) : null}
                {observed.per_seed.map((value, seed) => (
                  <a
                    aria-label={`Seed ${seed}: ${percent(value)}. View evidence.`}
                    className="accuracy-variance__seed"
                    href={armEvidenceUrl(study.study_id, `seed-${seed}`)}
                    key={`${key}-${seed}`}
                    style={{ left: `${position(value)}%` }}
                    title={`Seed ${seed}: ${percent(value)}`}
                  />
                ))}
                <span
                  className="accuracy-variance__mean"
                  style={{ left: `${position(observed.mean)}%` }}
                  title={`Mean ${percent(observed.mean)}`}
                />
              </div>
              <code>{interval(metric)}</code>
            </div>
          );
        })}
      </div>

      <figcaption>
        Points are final sample-weighted validation accuracies for five independent
        training seeds. Diamonds are arithmetic means. Horizontal lines are
        descriptive Student t intervals across those seeds; they are not equivalence
        tests. Dashed markers show the paper-reported mean when the model has one.
      </figcaption>
    </figure>
  );
}
