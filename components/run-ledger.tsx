import {
  armEvidenceUrl,
  formatAsOf,
  formatSigned,
  stateMeta,
  studyCounts,
  type ArmState,
  type StudyArm,
  type StudyDocument,
} from "@/lib/study";

const stateOrder: ArmState[] = ["DONE", "RUNNING", "QUEUED", "FAILED", "ABORTED"];

function StateLabel({ state }: { state: ArmState }) {
  const meta = stateMeta[state];
  return (
    <span className={`run-state run-state--${state.toLowerCase()}`}>
      <span className="run-state__glyph" aria-hidden="true">
        {meta.glyph}
      </span>
      <span>{meta.label}</span>
      <span className="sr-only">. {meta.explanation}.</span>
    </span>
  );
}

function ProvenanceLabel({ value }: { value: StudyArm["provenance"] }) {
  return (
    <span
      className={`provenance provenance--${value.toLowerCase()}`}
      title={
        value === "EXACT"
          ? "Paper-pinned training stack"
          : "Documented compatibility training with exact-stack claim evaluation"
      }
    >
      {value}
      {value === "COMPAT" ? <sup>1</sup> : null}
    </span>
  );
}

function Effect({ arm }: { arm: StudyArm }) {
  const [low, high] = arm.metrics.release_prompt_bootstrap_95_ci;
  return (
    <span className="run-effect">
      <strong>{formatSigned(arm.metrics.release_reward_delta)}</strong>
      <span>
        [{formatSigned(low)}, {formatSigned(high)}]
      </span>
    </span>
  );
}

export function RunLedger({
  study,
  compact = false,
}: {
  study: StudyDocument;
  compact?: boolean;
}) {
  const counts = studyCounts(study.arms);

  return (
    <div className={compact ? "ledger ledger--compact" : "ledger"}>
      <div className="ledger__header">
        <div>
          <p className="section-kicker">Selected arm results</p>
          <h2>
            {study.arms.length} selected arms · {study.completion.tracks.length} tracks
          </h2>
        </div>
        <p className="ledger__summary">
          {stateOrder
            .filter((state) => counts[state] > 0)
            .map((state) => `${counts[state]} ${stateMeta[state].label.toLowerCase()}`)
            .join(" · ")}
          <br />
          <span>reported {formatAsOf(study.as_of_utc)} UTC</span>
        </p>
      </div>

      <div
        className="ledger-track"
        aria-label={`Visual summary of all ${study.arms.length} selected arm states`}
      >
        {study.arms.map((arm) => (
          <span
            className={`ledger-track__arm ledger-track__arm--${arm.state.toLowerCase()} ${
              arm.provenance === "COMPAT" ? "is-compat" : ""
            }`}
            key={arm.arm_id}
            title={`Arm ${arm.ordinal}, Track ${arm.track}: ${arm.model_label}, ${arm.dataset_label}, ${stateMeta[arm.state].label}`}
          >
            <span className="sr-only">
              Arm {arm.ordinal}, Track {arm.track}: {arm.model_label}, {arm.dataset_label},{" "}
              {stateMeta[arm.state].label}
            </span>
          </span>
        ))}
      </div>

      <div
        className="table-scroll"
        tabIndex={0}
        aria-label="Scrollable selected-arm results table"
      >
        <table className="run-table">
          <caption>
            Selected terminal arms for the released-code and manuscript-method tracks.
            Row verdicts are directional assessments; the study verdict appears below.
          </caption>
          <thead>
            <tr>
              <th scope="col">Arm</th>
              <th scope="col">Track</th>
              <th scope="col">State</th>
              <th scope="col">Configuration</th>
              <th scope="col">GPU</th>
              <th scope="col">Profile</th>
              <th scope="col">Release Δ [95% CI]</th>
              <th scope="col">Direction</th>
              <th scope="col">Evidence</th>
            </tr>
          </thead>
          <tbody>
            {study.arms.map((arm) => (
              <tr key={arm.arm_id}>
                <th scope="row">{String(arm.ordinal).padStart(3, "0")}</th>
                <td>
                  <span className="track-label">{arm.track}</span>
                </td>
                <td>
                  <a
                    className="ledger-deep-link"
                    href={armEvidenceUrl(study.study_id, arm.arm_id, "#execution")}
                  >
                    <StateLabel state={arm.state} />
                  </a>
                </td>
                <td>
                  <strong>{arm.model_label}</strong>
                  <span>{arm.dataset_label}</span>
                </td>
                <td>
                  {arm.gpu}
                  <span>{arm.host}</span>
                </td>
                <td>
                  <a
                    className="ledger-deep-link"
                    href={armEvidenceUrl(study.study_id, arm.arm_id, "#provenance")}
                  >
                    <ProvenanceLabel value={arm.provenance} />
                  </a>
                </td>
                <td>
                  <Effect arm={arm} />
                </td>
                <td className={`run-verdict run-verdict--${arm.verdict.toLowerCase()}`}>
                  <a href={armEvidenceUrl(study.study_id, arm.arm_id, "#comparison")}>
                    {arm.verdict}
                  </a>
                </td>
                <td>
                  <a
                    className="run-evidence-link"
                    href={armEvidenceUrl(study.study_id, arm.arm_id)}
                  >
                    View evidence <span aria-hidden="true">→</span>
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="ledger__notes">
        <p>
          <sup>1</sup> <strong>COMPAT</strong> marks training on a documented
          compatibility stack. Claim-level metrics for all such arms were reevaluated
          on the exact paper stack.
        </p>
        <p>
          Intervals are conditional on fixed checkpoints and retained generations.
          They do not estimate training-to-training or decoding-to-decoding variance.
        </p>
      </div>
    </div>
  );
}
