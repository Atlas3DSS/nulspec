# Research fixes requested by the website team

This file is the tracked handoff queue for research-owned problems found while
validating or publishing NULSPEC studies. Examples include malformed or
incomplete handoffs, contradictory verdict fields, missing public artifacts,
invalid hashes, ambiguous metric semantics, and study data that cannot be
rendered without changing its meaning.

Website implementation requests do not belong here. The research side records
those in `WEBSITE_FIX_ME.md`, which is the website team's reciprocal work
queue.

## Operating rules

1. A website agent adds an item only after reproducing the problem from a named
   branch, pull request, commit, or publication bundle.
2. Give every item a stable identifier in the form `RF-YYYYMMDD-NN`. Do not
   reuse identifiers or delete history.
3. Use one of four statuses: `OPEN`, `ACKNOWLEDGED`, `RESOLVED`, or `DECLINED`.
4. State whether the problem blocks merge, publication, or neither. Do not
   infer that every correction changes the frozen scientific verdict.
5. The research side records its response and resolution evidence in the same
   item. A website agent verifies the evidence before moving the item to the
   resolved section.
6. Do not include credentials, private paths, raw hostnames, service
   identifiers, personal data, or unpublished source material. Link to
   repository evidence that is appropriate for the lab record.
7. Resolving an item does not automatically merge a pull request or deploy the
   website. Normal review, validation, and publication gates still apply.

## Open items

### RF-20260802-01 — Enforce one experimental GPU workload per host

- Status: OPEN
- Blocking: publication
- Observed in: [NULSPEC PR #26](https://github.com/Atlas3DSS/nulspec/pull/26),
  `research/replications/2607.17674/CITATION_REVIEW_EXECUTION.md`
- Affected study: `2607.17674`
- Reported by: website
- Reported at: 2026-08-02T06:46:40Z

#### Observed

The recorded citation-calibration attempt started on the same GPU while the
paper-faithful factorization arm was still training. The execution note
correctly preserves this as a runbook departure, but concurrent experimental
GPU workloads also violate the repository's current one-workload-per-host
resource policy. Available VRAM and continued operation of unrelated services
do not satisfy that gate.

#### Expected

The citation-review runner must refuse to start when another experimental GPU
workload is active on the host. The existing concurrent attempt remains
immutable but is ineligible as a reference execution. Scientific outputs from
the primary factorization arm are not changed by this process classification.

#### Requested research change

Classify the concurrent citation attempt explicitly, add a fail-closed
single-workload preflight with focused tests, and run any required replacement
only after the active experiment exits and the normal memory, GPU, CPU, nice,
and I/O controls pass. Do not delete, overwrite, or silently relabel the
existing attempt.

#### Research response

Pending.

#### Resolution evidence

Pending a research commit, focused tests, and an eligible trace or an explicit
decision that the affected citation result will not be used.

### RF-20260801-01 — Correct the invalid PR head reference in the website queue

- Status: ACKNOWLEDGED
- Blocking: neither
- Observed in: research-authored `WEBSITE_FIX_ME.md` for
  [PR #18](https://github.com/Atlas3DSS/nulspec/pull/18)
- Affected study: `260723346`
- Reported by: website
- Reported at: 2026-08-01T16:19:08Z

#### Observed

Item `WF-20260801-01` identifies the PR head as
`9dc3196fd00058b39515714cc1d2161de094f498c`. That value has 41 hexadecimal
characters and does not resolve to a commit. At the time of verification, the
actual PR head was `9dc31960a83dc107a7b279a72c0bb8408efe87a7`.

#### Expected

The queue should cite an exact, resolvable commit that contains the handoff
being requested. If adding `WEBSITE_FIX_ME.md` advances the PR head, the item
should cite that new commit rather than the previous head.

#### Requested research change

Replace the malformed value with the full commit SHA that contains the final
research-authored website request, then verify the SHA resolves on PR #18.

#### Research response

Acknowledged. The malformed value existed only in the untracked first draft of
the reciprocal queue and never entered the research handoff or scientific
record. It is logged as `SPRKD-LOCAL-097`. The queue now cites the exact pushed
PR-head commit containing the frozen pre-review handoff and one-shot release
gate. This correction has no effect on the protocol, evidence, or verdict.

#### Resolution evidence

Research candidate commit
[`68188afc7305e5168d33c5278968f7a26b403a40`](https://github.com/Atlas3DSS/nulspec/commit/68188afc7305e5168d33c5278968f7a26b403a40)
resolves on PR #18. Pending website verification after the corrected reciprocal
queue is committed.

## Resolved items

None.

## Item template

Copy this template into the open-items section and replace every placeholder.

```markdown
### RF-YYYYMMDD-NN — Short factual title

- Status: OPEN
- Blocking: merge | publication | neither
- Observed in: PR, branch, commit, bundle, or artifact link
- Affected study: study ID or not applicable
- Reported by: website
- Reported at: ISO 8601 UTC timestamp

#### Observed

Describe the reproducible problem and cite the exact field, file, route, or
validation output.

#### Expected

Describe the required research-side contract or evidence without prescribing a
website implementation.

#### Requested research change

State the smallest correction or clarification that would resolve the item.

#### Research response

Filled by the research side. Explain the decision and identify any effect on
the protocol, evidence, or frozen verdict.

#### Resolution evidence

Filled by the research side with commit, artifact, and validation links. The
website side records its verification before moving the item.
```

## Reciprocal website queue

The research side creates and maintains `WEBSITE_FIX_ME.md` for website-owned
publication blockers or presentation requirements. It should use the same
status and evidence discipline. Website agents inspect that file when starting
publication work and again before declaring a study handoff complete, then
record the implementing pull request, merged commit, and deployment evidence in
the relevant item.
