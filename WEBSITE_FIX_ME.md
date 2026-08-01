# Website fixes requested by the research team

This file is the tracked handoff queue for website-owned problems or
presentation requirements found while validating and publishing NULSPEC
studies. Research-data or evidence problems do not belong here; the website
side records those in `RESEARCH_FIX_ME.md`.

## Operating rules

1. Research adds an item only after identifying the affected study, handoff,
   commit, or public route.
2. Give every item a stable identifier in the form `WF-YYYYMMDD-NN`. Do not
   reuse identifiers or delete history.
3. Use one of four statuses: `OPEN`, `ACKNOWLEDGED`, `RESOLVED`, or `DECLINED`.
4. State whether the problem blocks merge, publication, or neither.
5. The website side records its response and implementation evidence in the
   same item. Research verifies meaning and evidence before the item moves to
   the resolved section.
6. Do not include credentials, private paths, raw hostnames, service
   identifiers, personal data, or unpublished source material.
7. Resolving an item does not automatically merge a pull request or deploy the
   website. Normal review, validation, and publication gates still apply.

## Open items

### WF-20260801-01 — Import typed classification-accuracy studies

- Status: OPEN
- Blocking: publication
- Observed in: [NULSPEC PR #18](https://github.com/Atlas3DSS/nulspec/pull/18),
  head commit `de208e670de4dd9a902e531679b6acdba21ff9a5`
- Affected study: `260723346` (`sprkd-malaria`)
- Reported by: research
- Reported at: 2026-08-01T16:15:57Z

#### Observed

The validated handoff uses
`nulspec-classification-accuracy-study-handoff-v1` with metric schema
`sprkd_trial_accuracy_v1`. The current canonical importer and arm pages accept
the earlier reward-delta/prompt-bootstrap shape, so importing this study would
require changing the meaning of its accuracy and fresh-training uncertainty.
Research therefore left `canonical_site_import` as
`blocked_pending_typed_accuracy_frontend`.

#### Expected

The site should ingest and render the handoff without relabeling accuracy as
reward, treating five training seeds as prompts, or presenting a descriptive
Student t interval as an equivalence test. It should preserve the distinct
study-level assessments **Not replicated** and **Underlying method
inconclusive**, and label the 94.792% supervised-logit result as post-hoc rather
than as the frozen replication result.

Each seed row should have a keyboard-focusable evidence route at
`/studies/260723346/arms/seed-{seed}`. The study should also expose the six
immutable choices behind **Vote to extend this paper**; votes schedule new
evidence and never rewrite the frozen result.

The importer must also enforce `final_peer_review`. Fable receives exactly one
review submission: `PASS` authorizes publication and a normal `FAIL` authorizes
it only after the exact three-action closure. After a technical `HARD_FAIL`,
only independently schema-valid PASS decisions from both the pinned GLM and
Kimi reviewers can satisfy the publication gate; a malformed, truncated,
refused, or non-PASS result remains a hard fail for human review. There is no
Fable resubmission, fallback retry, or tiebreaker. Author-email dispatch is a
separate gate and always requires final human approval of the exact hashed
draft and applicable disposition; external review can make the draft eligible
but can never authorize or send it.

#### Requested website change

1. Add a typed importer/validator for the handoff and metric schemas above.
2. Render the study overview, five run-level evidence pages, paired comparison
   details, provenance/integrity links, and separately labeled diagnostics from
   `WEBSITE_HANDOFF.json` without recomputing research values.
3. Wire the extension-vote control to the handoff's stable choice identifiers.
4. Enforce and render the one-shot final-review state and the distinct mandatory
   human author-email approval state without treating either as scientific
   evidence.
5. Record the implementing PR, merged commit, production route, and validation
   evidence below.

#### Website response

Pending.

#### Resolution evidence

Pending research-side verification after implementation and deployment.

### WF-20260801-02 — Balance audit evidence with contribution and learning

- Status: OPEN
- Blocking: publication
- Observed in: live home page, Study 260725091, and a linked arm-evidence page
  reviewed at 2026-08-01T16:48:50Z
- Affected study: all studies; first required for `260723346`
- Reported by: research
- Reported at: 2026-08-01T16:48:50Z

#### Observed

The live study is scientifically careful and visually coherent, but the page
allocates more space and earlier placement to the run ledger, deviations,
warning states, and verdict machinery than to the original contribution, what
reproduced, what the released artifacts enabled, what the replication taught,
and what evidence would resolve uncertainty. The result can therefore feel
prosecutorial even where individual sentences are fair. Authors are not
identified on the study page, and NULSPEC's own mistakes are less visible than
limitations of the upstream record.

In practical terms, the current site is an excellent index and appendix, but it
asks that layer to do the work of an explainer. It makes the receipts easy to
find without first telling a general reader what happened, why it matters, or
what they should carry forward.

The complete evidence and recommendations are in
`PUBLISHING_PRESENTATION_REVIEW.md`.

#### Expected

Before the detailed ledger, each study should present original authors and
contribution, exact tested scope, equally ranked “What held up” and “What did
not,” unresolved questions, learning value, and the next decisive evidence.
Credit released assets explicitly. Pair limits of the public record with limits
and mistakes during our replication. Provide a versioned author-response path.
Keep every verdict, null, error, deviation, and artifact accessible without
making audit machinery the dominant narrative.

#### Requested website change

1. Implement the result-at-a-glance hierarchy and progressive disclosure in
   `PUBLISHING_PRESENTATION_REVIEW.md`.
2. Add typed presentation fields supplied by research; do not infer or invent
   contribution, credit, learning, or author-response copy in the frontend.
3. Move the complete arm ledger below the balanced result narrative on study
   pages and substantially abbreviate it on the home page.
4. Render upstream-record limitations and replicator limitations with equal
   visual rank.
5. Record the implementing PR, production route, screenshots, accessibility
   checks, and research-side meaning verification below.

#### Website response

Pending.

#### Resolution evidence

Pending research-side verification after implementation and deployment.

### WF-20260801-03 — Render reviewer provenance, costs, and fail-closed consensus

- Status: OPEN
- Blocking: publication
- Observed in: [NULSPEC PR #18](https://github.com/Atlas3DSS/nulspec/pull/18),
  head commit `de208e670de4dd9a902e531679b6acdba21ff9a5`
- Affected study: `260723346` (`sprkd-malaria`); reusable for later studies
- Reported by: research
- Reported at: 2026-08-01T18:16:18Z

#### Observed

Fable's one permitted submission ended in a safeguard refusal with no review
findings and a $3.224742 charge. The human-directed GLM/Kimi fallback produced
two raw PASS declarations, but neither primary response was schema-valid; a
later valid GLM recovery call is retained but ineligible. The supplemental
disposition therefore remains `HARD_FAIL`. Six provider events cost
$4.44176232 in total.

Research now supplies an append-only public event/cost ledger, a sanitized
training-ready trace projection, the pinned model manifest, and human- and
machine-readable consensus records. Exact provider envelopes remain private by
hash because they contain request/session identifiers and machine context.

#### Expected

The study page should show external review as release-governance provenance,
not scientific evidence. Render the total and per-event costs—including what a
refusal cost—plus declared versus validated verdicts and why an event was
excluded. Link the sanitized traces and ledgers. Do not expose credentials,
provider request/session IDs, UUIDs, private paths, or raw provider envelopes.

The importer must fail closed unless both consensus-eligible GLM/Kimi rows are
structured-valid PASS decisions bound to the same frozen packet. A later retry
cannot replace either row. The current record must remain blocked for human
review, and author-email dispatch must remain independently blocked pending
final human approval of the exact draft.

#### Requested website change

1. Import and validate the external-review ledger, model manifest, and
   supplemental consensus schemas without recomputing their outcomes.
2. Render the cost/event chronology and sanitized trace links behind a compact
   review-provenance summary.
3. Enforce the two-valid-PASS rule, no-retry exclusion, and separate mandatory
   human email-approval gate.
4. Add privacy tests that reject request/session IDs, UUIDs, credentials, and
   private paths in public reviewer artifacts.
5. Record the implementing PR, production route, screenshots, validator tests,
   and research-side semantic verification below.

#### Website response

Pending.

#### Resolution evidence

Pending research-side verification after implementation and deployment.

## Resolved items

None.

## Item template

```markdown
### WF-YYYYMMDD-NN — Short factual title

- Status: OPEN
- Blocking: merge | publication | neither
- Observed in: PR, branch, commit, bundle, artifact, or public route
- Affected study: study ID or not applicable
- Reported by: research
- Reported at: ISO 8601 UTC timestamp

#### Observed

Describe the reproducible website-owned problem and cite exact evidence.

#### Expected

Describe the required presentation or publication behavior without changing
the meaning of the research record.

#### Requested website change

State the smallest website change that would resolve the item.

#### Website response

Filled by the website side with its decision and implementation scope.

#### Resolution evidence

Filled by the website side with PR, commit, checks, and deployment route.
Research records verification before the item moves to the resolved section.
```

## Reciprocal research queue

Website agents record research-owned blockers in `RESEARCH_FIX_ME.md`.
Research checks that file while a study is being published and again before
declaring the handoff complete, then records its response and evidence in the
relevant item.
