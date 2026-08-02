# Citation-audit execution amendment v1.0.3

This prospective trace-only amendment is frozen after the first Qwen citation
calibration was classified as ineligible under the host concurrency policy and
before any eligible replacement review. It does not change the v1.0.1 evidence
packets, source ordering, calibration set, prompts, schemas, reviewer model,
generation settings, retry budget, validation rules, review-plan hashes, or the
v1.0.2 runtime compatibility amendment.

The primary reproduction harness and citation runner previously relied on a
written one-experimental-workload-per-host policy but did not both enforce it.
Version 1.0.3 makes the citation runner acquire the same host-wide
`nulspec-experiment.lock` used by the primary runner. Acquisition is exclusive
and nonblocking. It occurs before route inspection, model requests, or creation
of a trace directory; contention terminates the process without a citation
attempt. The open lock handle is retained for the citation runner's entire
lifetime and its held state and mechanism are recorded in private run input.

The failed concurrent calibration remains immutable and retains zero decision
and evidentiary weight. A replacement calibration must use a fresh trace
directory, the v1.0.2 runtime contract, and an uncontended v1.0.3 host lock.
Starting an idle model server does not waive the lock: if the citation runner
reports contention, the server must be stopped without issuing a review
request.

The amended runner is frozen by tag
`2607.17674-citation-audit-harness-v1.0.3`. The parent evidence contract remains
`2607.17674-citation-audit-v1.0.1` and the decoding/runtime contract remains
`2607.17674-citation-audit-runtime-v1.0.2`.
