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

- Status: ACKNOWLEDGED
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

The concurrent calibration remains immutable, is explicitly classified as
ineligible, and has zero citation or scientific evidentiary weight. Prospective
harness v1.0.3 makes the Qwen citation runner acquire the same exclusive,
nonblocking host lock as every primary arm before route inspection, trace
creation, or a model request. It retains the lock for the process lifetime and
records the held state and mechanism in private run input. The earlier
concurrent one-token schema check is also classified as diagnostic-only;
preflight v1.0.1 now shares the lock. A replacement calibration will not start
until the primary workload releases that lock, an uncontended preflight passes,
and a fresh append-only trace is allocated.

Those execution conditions have now been satisfied. The eligible replacement
preflight and calibration both acquired the workstation lock while no other
NULSPEC experiment was active on that host. The completed calibration contains
six final reviews, ten occurrence decisions, a terminal completion record, a
297-file private content index, exact local usage/timing accounting, and a
separate Codex gate. The gate permits only the remaining Qwen first pass; it
continues to block teacher input, training use, publication, and email.

#### Resolution evidence

[Commit `cad3c93`](https://github.com/Atlas3DSS/nulspec/commit/cad3c933a810c9cc700dc3cd462a96a66dabd1d2)
and tag `2607.17674-citation-audit-harness-v1.0.3` contain the amendment,
implementation, focused tests, runbook, and error-ledger update. All 51
citation tests passed; Ruff lint and formatting passed; the frozen protocol
validator passed. Read-only live probes against each host's active primary arm
both received the registered contention rejection. [Commit
`a5263c0`](https://github.com/Atlas3DSS/nulspec/commit/a5263c09f98e298abe7d694faf571e16bc74975a)
and tag `2607.17674-citation-runtime-preflight-v1.0.1` extend the same guard to
schema preflight; host-specific probes rejected contention without creating a
trace. Final resolution remains pending an eligible fresh preflight and
calibration trace plus website-side verification. The eligible replacement is
now recorded in `CITATION_REVIEW_EXECUTION.md`; its private record-stream digest
is `c0771fbc34ca8862a878fbad13458fe1da48f4d7872a7059707a3cdf18fbdee7`,
and the tracked record deliberately exposes no private host path or raw trace.
Website verification remains pending, so this item stays acknowledged.

### RF-20260801-02 — Add the recorded human-disposition path for Fable HARD_FAIL

- Status: OPEN
- Blocking: publication
- Observed in: [NULSPEC PR #18](https://github.com/Atlas3DSS/nulspec/pull/18),
  commit `9cc6bafba42f19b144f45d02c9c1d71ac4ea9816`
- Affected study: `260723346`
- Reported by: website
- Reported at: 2026-08-01T17:01:17Z

#### Observed

The one permitted Fable invocation ended in `HARD_FAIL` because of a technical
safeguard refusal. It did not produce a substantive scientific review. The
frozen protocol states that publication may proceed after a recorded human
disposition, but `scripts/fable_final_review.py` exposes only `build-packet`,
`review-once`, `check-gate`, and `self-test`. Its gate evaluation always leaves
`HARD_FAIL` at `blocked_pending_human_review`, and the website handoff contains
no human-disposition record or authorized post-disposition state.

#### Expected

Research should define one machine-readable, deterministic way to record a
human decision after `HARD_FAIL`. It must preserve the original one-shot result,
bind the decision to the exact review packet and review result, identify whether
publication is authorized or remains blocked, and keep author-email approval as
a separate mandatory gate. It must not retry Fable or treat the safeguard
refusal as scientific evidence.

#### Requested research change

Add and test the human-disposition schema and command, document the required
fields and allowed decisions, regenerate `WEBSITE_HANDOFF.json`, and expose an
auditable publication state that the typed website importer can enforce. Do not
record an authorization unless an authorized human has explicitly made that
decision.

#### Research response

Pending.

#### Resolution evidence

Pending a research commit, deterministic tests, regenerated handoff, and
website verification.

### RF-20260801-03 — Add GLM and Kimi review after a technical Fable refusal

- Status: OPEN
- Blocking: publication
- Observed in: Fable refusal `FR-20260801-001` from
  [NULSPEC PR #18](https://github.com/Atlas3DSS/nulspec/pull/18), commit
  `9cc6bafba42f19b144f45d02c9c1d71ac4ea9816`
- Affected study: `260723346`
- Reported by: website
- Reported at: 2026-08-01T17:45:52Z

#### Observed

Fable refused the completed review packet under its biomedical safeguard,
charged $3.224742, and returned zero substantive findings. Its own wrapper
recommended configuring a fallback model. The current research runner preserves
the refusal and stops for a human, but it has no independent fallback-review
path.

#### Expected

After a Fable safeguard or technical refusal, preserve the exact Fable attempt
and submit the same immutable review packet independently to the pinned current
GLM and Kimi model revisions through OpenRouter. Prefer two successful reviews
and require at least one valid structured review before human disposition. Each
attempt must record the exact canonical model slug, packet and response hashes,
usage, cost, terminal state, and any refusal. Credentials remain only in ignored
environment configuration.

As selected from OpenRouter's catalog on 2026-08-01, the current revisions are
`z-ai/glm-5.2-20260616` and `moonshotai/kimi-k3-20260715`. Model selection must
be recaptured for later attempts rather than silently treating these names as
permanent.

#### Requested research change

Add a deterministic supplemental-review protocol and runner, retain both raw
attempts outside public Git, publish sanitized structured results with hashes,
and bind them into the human-disposition record. Do not retry Fable, rewrite the
frozen replication verdict, or allow a fallback model to authorize the author
email.

#### Research response

Pending.

#### Resolution evidence

Pending the protocol, runner, GLM and Kimi attempt records, deterministic
validation, regenerated handoff, and website verification.

### RF-20260801-04 — Separate the three-reviewer release gate from the Qwen teacher loop

- Status: OPEN
- Blocking: publication
- Observed in: the Fable refusal taxonomy, supplemental-review gate, and the
  completed direct-Codex Qwen outer-teacher audit
- Affected study: `260723346` and future studies using external release review
- Reported by: website
- Reported at: 2026-08-01T20:00:00Z

#### Observed

The existing study contract labels a Fable safeguard non-response as a
technical `HARD_FAIL`, invokes GLM and Kimi only after that event, and retains a
mandatory human publication disposition. The updated lab policy requests
Fable, GLM, and Kimi independently for every eligible review and distinguishes
a provider non-response from a substantive scientific decision.

The completed extension also used Qwen as the primary reviewer and Codex as its
single outer teacher. That historical audit remains valid as recorded. The
future recurring teacher loop needs independent GLM and Kimi audits followed by
Codex, with complete traces suitable for longitudinal harness analysis. Fable
must not be used in that recurring loop because its cost is reserved for the
separate final-release review.

#### Expected

- Always request Fable, GLM, and Kimi on the same immutable packet.
- Record a Fable safeguard or technical non-response, its tokens, cost, message,
  and hashes with decision weight zero. It is not a scientific `HARD_FAIL`.
- After a zero-weight Fable non-response, two independently valid GLM and Kimi
  `PASS` decisions authorize publication of the bound release.
- When Fable returns a substantive review, require valid `PASS` decisions from
  all three reviewers.
- Create scientific `HARD_FAIL` only from a valid substantive Fable `fail`.
  Malformed output, missing GLM/Kimi evidence, or disagreement blocks for human
  adjudication instead of being converted into a verdict.
- Keep author-email dispatch behind separate human approval of the exact draft.
- For Qwen-primary studies, send only the GLM and Kimi teacher records to Codex
  for outer trace/scope adjudication. Launch GLM and Kimi concurrently from the
  same immutable packet. Preserve every invalid invocation, diagnose and log
  its repair, and issue a new linked attempt; do not let Codex start until both
  logical teacher chains contain valid audits. Do not invoke Fable in that
  teacher loop.
- After ten distinct paper teacher pipelines are complete and validated,
  record a fresh 256-bit seed, reproducibly sample three of the ten, and request
  one bounded Fable critique containing those three pipelines. Keep it outside
  teacher consensus with zero decision weight, reject batch or paper reuse,
  and preserve its full selection, trace, and cost without automatic retry.

#### Requested research change

Version both protocols and schemas; do not rewrite raw historical attempts.
Adopt `extension/review_hierarchy.py` and `docs/REVIEW_HIERARCHY.md` for the
GLM/Kimi/Codex teacher loop. Keep the Fable/GLM/Kimi decision rule confined to
the final-release workflow. Regenerate the study handoff under the new release
policy when applicable and bind sanitized summaries into the publication
bundle. Preserve every raw prompt, request, response, usage/cost record, timing,
parsed result, failure, repair link, teacher-chain event, and Codex event in the
ignored archive. Each repair must use a new attempt ID and preserve the failed
attempt unchanged. Exhausting the bounded repair budget blocks the run rather
than accepting invalid evidence.

#### Research response

Pending.

#### Resolution evidence

Pending a versioned research-side contract, deterministic tests, regenerated
handoff, and one completed end-to-end three-reviewer hierarchy run.

## Resolved items

### RF-20260801-01 — Correct the invalid PR head reference in the website queue

- Status: RESOLVED
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
resolves on PR #18 and is the exact commit cited by `WF-20260801-01`. Website
verification confirmed both the commit object and the PR head on 2026-08-01.

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
