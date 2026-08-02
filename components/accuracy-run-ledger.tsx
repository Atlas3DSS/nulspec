import { HorizontalScrollRegion } from "@/components/horizontal-scroll-region";
import {
  armEvidenceUrl,
  formatAsOf,
  type AccuracyStudyDocument,
} from "@/lib/study";

function accuracy(value: number) {
  return `${value.toFixed(3)}%`;
}

export function AccuracyRunLedger({
  study,
  compact = false,
}: {
  study: AccuracyStudyDocument;
  compact?: boolean;
}) {
  return (
    <div className={compact ? "ledger accuracy-ledger ledger--compact" : "ledger accuracy-ledger"}>
      <div className="ledger__header">
        <div>
          <p className="section-kicker">Frozen primary trials</p>
          <h2>{study.arms.length} independent training seeds</h2>
        </div>
        <p className="ledger__summary">
          {study.arms.length} complete
          <br />
          <span>reported {formatAsOf(study.as_of_utc)} UTC</span>
        </p>
      </div>

      <HorizontalScrollRegion label="Scrollable frozen-seed accuracy table">
        <table className="run-table accuracy-run-table">
          <caption>
            Final sample-weighted full-validation accuracy. Each row is single-seed
            evidence and does not carry a study verdict.
          </caption>
          <thead>
            <tr>
              <th scope="col">Seed</th>
              <th scope="col">GPU</th>
              <th scope="col">Control-S</th>
              <th scope="col">SPRKD · exact</th>
              <th scope="col">SPRKD · intent</th>
              <th scope="col">Response KD · intent</th>
              <th scope="col">Evidence</th>
            </tr>
          </thead>
          <tbody>
            {study.arms.map((arm) => (
              <tr key={arm.arm_id}>
                <th scope="row">
                  <span className="accuracy-seed-label">Seed {arm.seed}</span>
                  <small>complete</small>
                </th>
                <td>
                  {arm.gpu.replace("NVIDIA ", "")}
                  <span>{arm.integrity.n_validation_targets.toLocaleString()} validation samples</span>
                </td>
                <td>{accuracy(arm.metrics.control_student)}</td>
                <td>{accuracy(arm.metrics.exact_public_sprkd)}</td>
                <td>{accuracy(arm.metrics.paper_intent_sprkd)}</td>
                <td>{accuracy(arm.metrics.paper_intent_response_kd)}</td>
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
      </HorizontalScrollRegion>

      <div className="ledger__notes">
        <p>
          Exact and paper-intent paths are shown separately. Accuracy is never
          relabeled as reward, and these five seeds are not prompt samples.
        </p>
      </div>
    </div>
  );
}
