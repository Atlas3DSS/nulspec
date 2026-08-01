# Frontend handoff: SPRKD run-level evidence

## Study-level outcome

Render the replication outcome as **Not replicated** and the underlying-method
assessment as **Inconclusive**. The public final-epoch path did not reproduce
the reported stable 94.80% result: exact-public SPRKD averaged 85.742% with one
chance-level final, and narrow paper-intent SPRKD averaged 67.977% with three.
The latter trailed unmodified-weak-teacher RKD (71.507%) by 3.530 points. Also
show the non-verdict-bearing best-epoch context—94.827% exact and 94.149%
paper-intent—because it explains why missing checkpoint-selection provenance
matters. Do not render “not replicated” as “method disproved.”

Show a separately labeled **post-hoc diagnostic** callout: correcting only the
supervised loss input produced five stable SPRKD finals with mean 94.792% (SD
0.193), but the paired corrected Control-S mean was 95.152%. This cannot alter
the primary classification and must not be displayed as the preregistered
replication. Link the callout to the loss-contract result and author-intent
question.

## Do not coerce accuracy into the reward schema

The current NULSPEC arm contract was built for reward deltas and prompt-level
bootstrap intervals. This study measures classification accuracy over five
independent training seeds. The frontend and publication validator must add a
typed accuracy projection; fields must not be renamed to “reward,” and the
five-seed t interval must not be described as prompt uncertainty.

## Canonical hierarchy

```text
Study → Frozen seed → Evidence layer/track → Model → Evaluation → Artifact
```

One public arm corresponds to one frozen primary trial (`seed-0` through
`seed-4`). A row may show the exact public-code and narrow paper-intent models
side by side because they share that seed's validation split. E1–E3 and D1–D2
remain separately labeled diagnostics and never replace the primary row.

Use the stable route:

```text
/studies/260723346/arms/seed-{seed}
```

Every run-table row needs a keyboard-focusable **View evidence** link. Suggested
fragments remain `#comparison`, `#execution`, `#provenance`, and `#evidence`.

## Typed metric projection

The machine analysis exposes exact run IDs, model keys, final sample-weighted
accuracy/loss, best/final history values, environment labels, and integrity
hashes. The public arm should declare
`metrics_schema: sprkd_trial_accuracy_v1` and
project these fields without recomputation:

- paper means: SPRKD 94.80, Control-S 94.47, response KD 70.10;
- exact public path: SPRKD and ASR-mutated-teacher RKD final accuracies;
- narrow paper-intent path: fresh-init SPRKD and untouched-weak-teacher RKD;
- shared Control-S final accuracy;
- within-row SPRKD-minus-Control-S and SPRKD-minus-RKD point differences;
- exact within-seed McNemar cells, p-value, and log10 p-value; and
- GPU label, software profile, selected checkpoint rule, and integrity hashes.

A single seed is not independently judged against a five-trial paper mean.
Per-seed rows should therefore say **single-seed evidence** rather than assign a
study-level reproduced/not-reproduced label. The study classification comes
from the complete five-seed aggregate.

## Arm page requirements

Each page should show:

1. the paper's three reported means beside this seed's exact and intent values;
2. final sample-weighted accuracy as the primary value and best epoch as a
   separately labeled stability diagnostic;
3. McNemar contingency cells and stable exact p-values only for models sharing
   this seed's validation split;
4. the neutral host/GPU/software profile and all input/result digests;
5. links to the one-page result, full report, machine JSON, protocols,
   upstream audit, and extension roadmap; and
6. a statement that five-seed t intervals estimate fresh-training variability
   over the frozen seeds and do not establish practical equivalence.

## Result artifacts and deep links

The website should copy only artifacts explicitly listed in
`WEBSITE_HANDOFF.json`. The primary overview figure links to the machine
analysis, while each plotted seed marker may link to its arm route. Do not link
ignored checkpoints, raw logs, citation source packets, private paths, raw
hostnames, service identifiers, IP addresses, or physical GPU UUIDs.

## Extension control

Render **Vote to extend this paper** with the six ranked choices in
`EXTENSION_ROADMAP.md`/`WEBSITE_HANDOFF.json`. Extension votes schedule new
evidence; they cannot rewrite the frozen classification or primary arm rows.
