# Frontend handoff: arm-level evidence drilldown

## User need

The current run ledger shows whether each selected arm directionally matches,
diverges, or is inconclusive, but its rows are terminal displays. Every result
should instead be a doorway into the evidence supporting that outcome.

The canonical hierarchy is:

```text
Study → Configuration → Arm → Attempt → Evaluation → Artifact
```

- A **configuration** is one model, dataset, and seed combination.
- An **arm** is the selected claim unit for one configuration and method track.
- An **attempt** is one immutable execution. Failed attempts and recoveries are
  retained, and recovery attempts are not independent replicates when they
  reuse prerequisites.
- An **outcome** is the claim-level result selected under the frozen protocol.
- An **artifact** is hash-bound evidence supporting an outcome.

## Phase-one implementation

The existing publication bundle already contains enough sanitized information
for an arm detail page. Add a stable route:

```text
/studies/{study_id}/arms/{arm_id}
```

Each ledger row must contain a keyboard-focusable **View evidence** link to that
route. Row-wide pointer behavior may supplement the link, but must not replace
it. Suggested deep links are:

- direction badge → `#comparison`;
- execution state → `#execution`;
- exact/compat profile → `#provenance`;
- artifact list → `#evidence`.

The arm page must show:

1. a plain-language arm summary;
2. the published result beside the release-protocol rerun and conditional 95%
   interval;
3. numerical inclusion and directional assessment as separate judgments;
4. the deterministic independent-paired endpoint and its within-track
   Holm-adjusted p-value;
5. selected execution, recovery, hardware, and stack provenance;
6. links to the study-level summary, full report, and machine analysis; and
7. the uncertainty limits that apply to this single-seed arm.

The source is the public `machine_analysis` artifact. Join on `arm_id`; do not
recompute or reinterpret the supplied values in the frontend.

## Interpretation guardrails

- `MATCH`, `DIVERGES`, and `INCONCLUSIVE` are arm-level **directional** labels.
  They are not the study classification.
- Display `published_delta_inside_release_interval` independently. An arm can
  agree in direction while missing the published point estimate.
- Every interval is conditional on fixed checkpoints and retained generations;
  it is not training-to-training or decoding-to-decoding uncertainty.
- The Holm-adjusted paired p-value belongs to the independent deterministic
  endpoint, not the sampled release endpoint.
- Keep the study-level `PARTIALLY_REPRODUCED` verdict visually distinct from
  any arm badge.
- Do not hide failed or superseded attempts once attempt-level evidence is
  available.

## Phase-two data dependency

Attempt timelines and direct raw-output links are not yet part of the public
projection. A future sanitized `arm-evidence-index.json` should add, per arm:

- the stable detail path and selected-outcome explanation;
- every attempt, terminal state, selection reason, and recovery parent;
- evaluation records and their protocols;
- immutable artifact URLs, media types, byte counts, and SHA-256 digests;
- related deviations and public error findings; and
- a copyable reproduction command.

Until that artifact exists, the frontend should show selected-arm metrics and
study-level evidence, label deeper attempt/raw-output drilldown as unavailable,
and never synthesize missing URLs or histories.

## Acceptance criteria

- All 30 table rows expose a named **View evidence** link.
- All 30 arm URLs are statically generated and return a page.
- Links work with keyboard navigation and do not depend on color or hover.
- The arm page separates numerical inclusion, direction, and study verdict.
- Conditional uncertainty is visible beside the affected estimates.
- Exact versus compatibility provenance and recovery status are visible.
- Missing attempt-level evidence is stated honestly.
- No page exposes private paths, usernames, raw hostnames, service identifiers,
  addresses, credentials, or GPU UUIDs.
- Site-data validation fails on duplicate arm IDs, unsafe route components, or
  a detail page whose arm is absent from the publication bundle.
