import Link from "next/link";
import {
  stateMeta,
  studyCounts,
  type ArmState,
} from "@/lib/study";

const statusOrder: ArmState[] = [
  "DONE",
  "RUNNING",
  "QUEUED",
  "FAILED",
  "ABORTED",
];

export function StatusStrip() {
  const counts = studyCounts();

  return (
    <div className="status-strip" role="status" aria-live="polite">
      <div className="shell status-strip__inner">
        <div className="status-strip__state">
          <span className="live-dot" aria-hidden="true" />
          <span>Study 001 — running</span>
          <span className="live-caret" aria-hidden="true">
            ▌
          </span>
        </div>
        <p>
          <span className="status-strip__counts">
            {statusOrder
              .filter((state) => counts[state] > 0)
              .map(
                (state) =>
                  `${counts[state]} ${stateMeta[state].label.toLowerCase()}`,
              )
              .join(" · ")}
            {" · "}
          </span>
          <span className="status-strip__warning">conclusions not final</span>
        </p>
        <Link href="/studies/001">Open ledger →</Link>
      </div>
    </div>
  );
}
