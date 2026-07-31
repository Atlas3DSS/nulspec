import {
  formatAsOf,
  stateMeta,
  study,
  studyCounts,
  type ArmState,
  type StudyArm,
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
          ? "Paper-pinned execution stack"
          : "Documented Blackwell-compatible execution stack"
      }
    >
      {value}
      {value === "COMPAT" ? <sup>1</sup> : null}
    </span>
  );
}

export function RunLedger({ compact = false }: { compact?: boolean }) {
  const counts = studyCounts();

  return (
    <div className={compact ? "ledger ledger--compact" : "ledger"}>
      <div className="ledger__header">
        <div>
          <p className="section-kicker">Live run ledger</p>
          <h2>{study.arms.length} frozen configurations</h2>
        </div>
        <p className="ledger__summary">
          {stateOrder
            .filter((state) => counts[state] > 0)
            .map((state) => `${counts[state]} ${stateMeta[state].label.toLowerCase()}`)
            .join(" · ")}
          <br />
          <span>as of {formatAsOf(study.as_of_utc)} UTC</span>
        </p>
      </div>

      <div className="ledger-track" aria-label="Visual summary of all 15 run states">
        {study.arms.map((arm) => (
          <span
            className={`ledger-track__arm ledger-track__arm--${arm.state.toLowerCase()} ${
              arm.provenance === "COMPAT" ? "is-compat" : ""
            }`}
            key={arm.arm_id}
            title={`Arm ${arm.ordinal}: ${arm.model}, ${arm.dataset}, ${stateMeta[
              arm.state
            ].label}`}
          >
            <span className="sr-only">
              Arm {arm.ordinal}: {arm.model}, {arm.dataset},{" "}
              {stateMeta[arm.state].label}
            </span>
          </span>
        ))}
      </div>

      <div className="table-scroll" tabIndex={0} aria-label="Scrollable run ledger">
        <table className="run-table">
          <caption>
            Track R execution ledger. DONE means only that a run finished; it is
            not a replication verdict.
          </caption>
          <thead>
            <tr>
              <th scope="col">Arm</th>
              <th scope="col">State</th>
              <th scope="col">Configuration</th>
              <th scope="col">GPU</th>
              <th scope="col">Provenance</th>
              <th scope="col">Verdict</th>
            </tr>
          </thead>
          <tbody>
            {study.arms.map((arm) => (
              <tr key={arm.arm_id}>
                <th scope="row">{String(arm.ordinal).padStart(3, "0")}</th>
                <td>
                  <StateLabel state={arm.state} />
                </td>
                <td>
                  <strong>{arm.model}</strong>
                  <span>{arm.dataset}</span>
                </td>
                <td>
                  {arm.gpu}
                  <span>{arm.host}</span>
                </td>
                <td>
                  <ProvenanceLabel value={arm.provenance} />
                </td>
                <td className="run-verdict">
                  {arm.verdict ?? <span aria-label="No verdict yet">—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="ledger__notes">
        <p>
          <sup>1</sup> <strong>COMPAT</strong> marks RTX PRO 6000 Blackwell arms.
          The paper-pinned PyTorch build cannot target <code>sm_120</code>; the
          substitution and required exact-stack re-evaluation are recorded as
          D-001.
        </p>
        <p>
          State is operational. Verdict remains blank until the frozen
          15-configuration family is complete and the analysis gate opens.
        </p>
      </div>
    </div>
  );
}
