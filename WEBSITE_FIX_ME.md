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
  head commit `9cc6bafba42f19b144f45d02c9c1d71ac4ea9816`
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
review submission: `PASS` authorizes publication, a normal `FAIL` authorizes it
only after the exact three-action closure, and `HARD_FAIL` stops for human
review. There is no Fable resubmission. Author-email dispatch is a separate
gate and always requires final human approval of the exact hashed draft; Fable
can make the draft eligible but can never authorize or send it.

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

The complete evidence and recommendations are in
`PUBLISHING_PRESENTATION_REVIEW.md`.

#### Expected

Before the detailed ledger, each study should present original authors and
contribution, exact tested scope, equally ranked “What held up” and “What did
not,” unresolved questions, learning value, and the next decisive evidence.
Credit released assets explicitly. Pair limits of the public record with limits
and mistakes in our replication. Provide a versioned author-response path.
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
