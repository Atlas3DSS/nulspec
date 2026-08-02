import Link from "next/link";
import {
  stateMeta,
  studyClassificationLabel,
  studyCounts,
  type ArmState,
  type AnyStudyDocument,
} from "@/lib/study";

const statusOrder: ArmState[] = ["DONE", "RUNNING", "QUEUED", "FAILED", "ABORTED"];

export function StatusStrip({ study }: { study: AnyStudyDocument }) {
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
            {studyClassificationLabel(study)}
          </span>
        </p>
        <Link href={`/studies/${study.study_id}`}>View study →</Link>
      </div>
    </div>
  );
}
