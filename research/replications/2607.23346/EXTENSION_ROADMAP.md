# Extension roadmap for arXiv:2607.23346

## Boundary

The frozen study closes with **not replicated** for the public five-seed final
result and **inconclusive** for the underlying method. The unusually close
best-epoch mean and the high/chance final mixture make provenance and stability
work more valuable than simply adding another favorable benchmark. The ranked
packages below create new evidence; none can retroactively convert a selected
checkpoint into the preregistered final metric.

Every follow-up receives a new prospectively committed protocol and attempt
tree. No extension may replace an unfavorable seed or rewrite the frozen
five-seed primary result.

The completed post-hoc loss-contract diagnostic makes the terminal-activation
factor especially high-value: it stabilized all five SPRKD runs near 94.80%
while leaving the scratch control slightly higher. That result strengthens the
case for author clarification and the prospective factorial below; it does not
promote the post-hoc arm into the replication result.

## Recommended work, in order

| Priority | Work package | Role | Question | Minimum useful design |
|---:|---|---|---|---|
| 1 | Author-intent reconciliation | Replication strengthening | Which historical implementation actually produced Table 1? | Obtain the canonical code revision, full arguments, environment, seeds, five per-trial records, checkpoint-selection rule, supervised/KD loss inputs, ASR selection, and Hessian provenance. Freeze those materials before any rerun. |
| 2 | Independent clean-room rerun | Reproducibility strengthening | Can a new operator reproduce our public result without private assistance? | Build the supplied CUDA container on an NVIDIA Container Toolkit host, give an independent operator only the public tag and acquisition instructions, record every ambiguity, and compare regenerated JSON and figure hashes. |
| 3 | Targeted stability and variance map | Robustness replication | Are the observed collapses and ordering stable across fresh training randomness? | Run at least 10 prospectively fixed seeds for the released path, the clarified author-intent path, and a scratch control. Save optimizer state and event-level ASR/NHE/PGD decisions; report seed variance, best/final divergence, and collapse incidence without exclusions. |
| 4 | Loss and initialization factorial | Mechanistic extension | Which visible implementation choices drive accuracy and stability? | On a diagnostic seed set, preregister a 2×2×2 design over terminal Softmax versus logits for supervised CE, direct-ASR versus fresh initialization, and last-snapshot versus lowest-loss ASR. Keep all remaining optimizer behavior identical. |
| 5 | Curvature provenance and common-data audit | Replication strengthening | Does the reported SPRKD < Control-S < RKD curvature ordering survive a fully specified estimate? | Acquire the original states/probes if available; otherwise freeze a common full-validation subset, loss input, probe count, random vectors, estimator tolerance, and checkpoint rule. Report raw probes and uncertainty, not only one trace. |
| 6 | Modern baseline and cross-dataset study | New extension | Does SPRKD add value beyond response KD on harder tasks? | After the malaria method is reconciled, compare against feature, relational, contrastive, and label-assisted KD across at least one nontrivial public dataset, multiple architectures, and multiple seeds with compute-normalized accounting. |

The first, second, third, and fifth packages strengthen replication. The fourth
and sixth are extensions: useful regardless of outcome, but not prerequisites
for closing the current study.

## Website vote contract

The study page should expose a button labeled **“Vote to extend this paper.”**
The single-choice prompt is **“Which follow-up would most improve confidence in
this result?”** The frontend owns identity, abuse controls, tallying, and
scheduling; the study owns these stable choices and their evidentiary roles:

1. Clarify and rerun author intent.
2. Run an independent clean-room reproduction.
3. Measure stability across more seeds.
4. Isolate loss, initialization, and ASR choices.
5. Reconstruct the curvature analysis.
6. Compare modern KD baselines and datasets.
