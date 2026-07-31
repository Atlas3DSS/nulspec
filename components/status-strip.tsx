import Link from "next/link";
import {
  classificationLabel,
  stateMeta,
  studyCounts,
  type ArmState,
  type StudyDocument,
} from "@/lib/study";

const statusOrder: ArmState[] = ["DONE", "RUNNING", "QUEUED", "FAILED", "ABORTED"];

export function StatusStrip({ study }: { study: StudyDocument }) {
  const counts = studyCounts(study.arms);

  return (
    <div className="status-strip" role="status" aria-live="polite">
      <div className="shell status-strip__inner">
        <div className="status-strip__state">
          <span className="live-dot live-dot--steady" aria-hidden="true" />
          <span>Study {study.study_id} — reported</span>
        </div>
        <p>
          <span className="status-strip__counts">
            {statusOrder
              .filter((state) => counts[state] > 0)
              .map((state) => `${counts[state]} ${stateMeta[state].label.toLowerCase()}`)
              .join(" · ")}
            {" · "}
          </span>
          <span className="status-strip__warning">
            {classificationLabel(study.verdict.classification)}
          </span>
        </p>
        <Link href={`/studies/${study.study_id}`}>Open result →</Link>
      </div>
    </div>
  );
}
