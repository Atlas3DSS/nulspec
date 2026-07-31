# Extension roadmap for arXiv:2607.25091

## Boundary

The frozen primary result is **partially reproduced**: we broadly reproduced
the released numerical table, but did not confirm universal stable convergence
or a robust capacity-headroom rule; actual output-quality improvement remains
unresolved. Follow-up work may sharpen, explain, or challenge that conclusion,
but it may not silently rewrite the 30-arm result. Every new run receives a
prospectively frozen protocol, immutable attempt directory, independent seed,
and a clearly labeled evidentiary role.

## Recommended work, in order

| Priority | Work package | Role | Question it can answer | Minimum useful design |
|---:|---|---|---|---|
| 1 | Author-intent reconciliation | Replication strengthening | Did source ambiguity cause us to execute a method the authors did not intend? | Send a neutral clarification packet requesting the canonical launcher, PPO budget, reward initialization and dtype, rollback semantics, stopping rule, evaluation settings, dependency/base revisions, reward checkpoints, arguments, logs, and raw 200-example records. Freeze any response as a new Track I before viewing outcomes. |
| 2 | Exact-stack training audit | Replication strengthening | Did compatibility training affect the eight arms trained outside the paper-era stack? | Rerun those eight arms on compatible accelerators under the exact reconstructed stack. Compare training health and deterministic endpoints; retain the current Blackwell-trained arms as disclosed evidence rather than replacing them. |
| 3 | Targeted variance map | Robustness replication | Are the three Track R misses, the positive anchor, and the rollback failure stable across fresh runs and decoding draws? | Add at least three independent training seeds to the three Track R numerical misses, SmolLM2-360M/WikiText as a positive anchor, and one Pythia-160M rollback-prone arm. For every checkpoint, run at least five preregistered sampled decoding replicates plus the deterministic paired endpoint. Report seed, decoding, and prompt uncertainty separately. |
| 4 | Track M component attribution | Mechanistic extension | Which of the three manuscript-stated changes caused the stability and reward shifts? | Run a preregistered 2×2×2 factorial over SFT-initialized reward training, float32 reward inference, and optimizer-state reset on a diagnostic subset containing a rollback-prone arm, the Pythia-410M/WikiText reversal, and a large positive SmolLM shift. Do not interpret the current bundled Track M contrast as a component effect. |
| 5 | Independent output-quality validation | Evaluation extension | Do PPO outputs actually improve outside their own reward model? | Use counterbalanced, blinded pair order; a frozen rubric; repeated judgments; a small human-audited calibration set; and an outer teacher that reviews reviewer reliability. Qwen remains a diagnostic. A version-pinned Codex-class reviewer can be the first outer teacher, with its disagreements and abstentions retained. |
| 6 | Independent clean-room audit | Reproducibility strengthening | Can another researcher reach the same result from the public repository alone? | Give a fresh operator only the tagged protocol, container/lock, hashes, and public instructions. Log every ambiguity before assistance and compare regenerated reports byte-for-byte. |

## Expansion rule

Do not immediately multiply all 15 configurations across every extension. Run
the diagnostic designs first. Expand to the full matrix when the diagnostic
result changes a claim-level interpretation, reveals important heterogeneity,
or shows that a full estimate is feasible and decision-relevant. A null pilot
is still publishable: it can show that a suspected source of variance or a
method correction does not materially explain the discrepancy.

The most defensible next compute project is the targeted variance map, while
the author packet proceeds in parallel without GPU time. Exact-stack retraining
is the highest-value check on our disclosed compatibility deviation. The
factorial and independent-quality studies are extensions, not prerequisites
for calling the present reproduction complete.

## Website handoff

The study page should expose a button labeled **“Vote to extend this paper.”**
The vote asks which follow-up would most improve confidence in the result and
offers the five research choices encoded in
[`publication/website-handoff.json`](../publication/website-handoff.json):
targeted variance, exact-stack retraining, Track M attribution, independent
output-quality review, or clean-room reproduction. The website owns the button,
identity/rate limiting, tally, and scheduling behavior; this repository owns
the frozen labels, descriptions, and evidentiary boundaries.
