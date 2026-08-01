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

- Status: ACKNOWLEDGED
- Blocking: publication
- Observed in: [NULSPEC PR #18](https://github.com/Atlas3DSS/nulspec/pull/18),
  head commit `68188afc7305e5168d33c5278968f7a26b403a40`
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

Accepted. Branch `agent/sprkd-site-publication` adds a discriminated
classification-accuracy publication type without modifying the existing
reward-delta type. Its importer validates the exact committed handoff, all five
terminal seeds, metric semantics, classifications, routes, extension choices,
artifact declarations, hashes, and a strict public artifact allowlist.

The importer separately enforces the one-shot Fable gate. It can validate
frontend compatibility while review is pending, but it refuses to create a
public bundle unless `publication_authorized` is true after `PASS` or the exact
three-action closure. `HARD_FAIL` cannot import. Author-email state is kept
separate: the draft is not copied publicly, its SHA-256 is retained, and
dispatch remains closed unless a distinct human approval binds the exact
draft. The study page renders both controls as release governance, not as
scientific evidence.

The overview and five seed pages render final accuracy, fresh-training
variability, paired point differences, exact McNemar cells, execution and
integrity provenance, separately labeled diagnostics, and the six stable
extension-vote identifiers. Browser checks cover desktop and mobile layouts,
keyboard-focusable evidence links, horizontal-table controls, tab behavior,
route allowlisting, and WCAG 2.1 AA rules when an authorized bundle is present.

At research commit `9cc6bafba42f19b144f45d02c9c1d71ac4ea9816`,
compatibility validation passes and the normal import rejects release state
`blocked_pending_human_review`. The one permitted Fable invocation ended in a
safeguard refusal and is not retried. No public route or study bundle is
retained while the required human disposition is absent.

#### Resolution evidence

Pending a recorded human disposition for the Fable `HARD_FAIL`, an authorized
research release gate, final bundle import, implementing PR checks and merge,
production deployment, and research-side semantic verification.

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
