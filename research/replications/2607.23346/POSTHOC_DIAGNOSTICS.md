# Post-hoc diagnostic register

## D1 — epoch-level training stability

**Specified:** 2026-08-01 after seeds 0 and 1 completed and before inspecting
seeds 2–4. This analysis is outcome-motivated and cannot alter the frozen
replication verdict.

Seed 1's integrity-validated paper-intent SPRKD history rose above 93% and then
dropped sharply to chance-level performance. The frozen runner retained all 500
epoch validation histories but not optimizer event state, so we added a
descriptive analyzer rather than inventing a mechanism after the fact.

For every completed seed and each of the six 500-epoch models, D1 reports:

- best validation batch-mean accuracy and its epoch;
- final validation batch-mean accuracy and the best-to-final drop;
- largest one-epoch accuracy loss and gain, with arrival epochs;
- final-50-epoch mean accuracy; and
- the number of sub-60% epochs after first reaching 85%.

No collapse threshold, exclusion rule, or confirmatory hypothesis test is
introduced. All values are exposed, and final sample-weighted accuracies remain
the primary outcomes. The next causal experiment should freeze event-level
logging for ASR targeting, NHE, and PGD; save optimizer state; and compare the
released no-revert behavior against the paper-described failed-move reversion.

## D2 — supervised loss-contract correction

**Specified:** 2026-08-01 after seeds 0–2 completed and before inspecting seeds
3–4. This is outcome-motivated, runs only after all preregistered work for its
seed, and cannot alter the frozen verdict.

The released malaria student ends in `Softmax`, while both Control-S and SPRKD
are optimized with PyTorch `CrossEntropyLoss`, whose input contract is
unnormalized logits. Seeds 1 and 2 showed sharp late accuracy losses, including
a seed-2 Control-S drop from 94.91% best to 50.50% final. D2 replaces only that
terminal `Softmax` with `Identity` for a paired scratch control and a paired
paper-intent SPRKD student. Split, seed, ASR, optimizer, learning rate, epoch
count, preprocessing, and every SPRKD default remain unchanged.

D2 reports all five paired outcomes and exact McNemar comparisons against the
released-loss counterparts. It can show whether obeying the loss API contract
stabilizes these runs; it cannot prove which internal event caused a historical
collapse. The runner directly hashes every base checkpoint it consumes and
retains SPRKD's final optimizer counters.
