# Upstream specification audit

This audit was completed before scratch training. Items are described neutrally:
the goal is to separate recoverable implementation choices from claims that
cannot be reconstructed from the release.

## Release chronology

The preserved training notebook and most malaria artifacts were committed in
February 2023. The paper-linked repository's current package, reproduction
script, tests, and executed analysis notebooks arrived together in commit
`7f1655f` on 2026-05-27 (commit message: “Created package and made old
repository accessible and usable”). arXiv v1 followed on 2026-07-25. The modern
script is therefore a public reimplementation around historical artifacts, not
a provenance-complete capture of the environment that produced every table
entry. This is why artifact replay, exact modern-script training, and narrow
paper-intent diagnostics are reported as distinct layers.

## Material conflicts

| Topic | Paper | Preserved 2023 notebook | 2026 reproduction package/script |
|---|---|---|---|
| Student epochs | 500, five trials | checked-in active cell says 10 | README/script default says 10; accepts 500; no five-trial wrapper |
| Student initialization | explicitly *not* initialized at ASR | extracts TLI target, resets/redeclares student | injects ASR into the same student it then trains |
| RKD teacher | two-epoch weak teacher | no recoverable RKD training cell | `inject_state_list(..., teacher=teacher_models[0])` overwrites teacher 0 with the ASR before RKD uses it |
| RKD response values | standard logit matching | malaria architectures end in Softmax; no recoverable RKD training cell | both models end in Softmax, then `train_response_kd` applies `log_softmax`/`softmax` to those probabilities again |
| Supervised loss input | cross-entropy between predictions and labels | terminal-Softmax architectures are passed to cross-entropy | terminal-Softmax probabilities are passed to PyTorch `CrossEntropyLoss`, whose input contract is unnormalized logits |
| Saddle rule | Equation 1 combines thresholded negative mass and a positive/negative condition | checked-in notebook uses a 0.4 negative/positive ratio | default is negative mass at least 7 only |
| Eigenvalue count | methods says 4 for students and 2–20 for teachers; limitations says 2 for students and 20 for teachers | configuration varies across notebook cells | reproduction leaves the package default of 4 for both teacher monitoring and student NHE |
| ASR selection | lowest-loss saddle from each teacher | last qualifying snapshot | `aggregate_asr` uses the last snapshot, although its docs call it lowest-loss |
| Epsilon | 0.1 in all experiments | constructor default 0.01; active cell passes 0.001 | default 0.001 |
| Transform weight | `1 - 2^(-t/10)` | `1 - 0.5*2^(-t/10)` | `1 - 0.5*2^(-t/10)` |
| Stagnation threshold | 0.02 | constructor 0.01; active cell 0.02 | default 0.01 |
| NHE | described as active | call is commented out in checked-in optimizer | active conditionally |
| PGD/revert | Gaussian variance 0.1 and revert failed moves | Hessian-scaled radius; revert code commented | fixed variance 0.1; no post-move verification/revert |
| Validation reporting | 175 checkpoints over 500 epochs; means over five trials | logs every validation minibatch (108/epoch) | logs one unweighted minibatch mean per epoch |

The package's end-to-end script also initializes `teacher_best_val_acc` as an
empty list and never populates it. It reports the best validation checkpoint,
whereas the paper does not clearly state best-versus-final model selection.
Table 1 identifies its entries as five-trial averages but provides no seeds,
per-trial values, dispersion, uncertainty interval, or failed-run handling, so
the release does not reveal whether the reported mean reflects stable final
convergence or run/checkpoint selection.

The released data loader applies a random 75/25 split to individual cell
images. The official NLM source describes a patient-derived dataset and
publishes patient-to-cell mapping files, but the reproduction path does not use
those groups to keep patients disjoint. This matches the paper's stated split;
it also means the result should be interpreted as image-level validation, not
evidence of held-out-patient or clinical-site generalization.

The response-KD mismatch is important but separable from the exact replication.
The released implementation is retained unchanged in Tracks B and C. It uses no
hard-label cross-entropy term and computes KL after applying a second softmax to
the networks' already-softmaxed outputs. Consequently, its result tests the
released baseline, not a conventional logit-KD baseline. Correcting that loss
would be an extension and is not substituted into the preregistered result.

## Released artifact observations (pre-training)

- The supplied `TESTSET.pth` contains exactly 100 images (54 class 0, 46 class
  1), despite a separate package comment referring to 64 samples.
- On that exact tensor set, released checkpoints score 84% (SPRKD), 80%
  (Control), and 74% (RKD). This matches the release notebook's own contingency
  table and relative ordering, but not Table 1's headline accuracies.
- The authors' executed 2026 analysis notebook explicitly notes that 100 samples
  cannot yield the reported `6.3e-87` McNemar p-value and says the paper used the
  full 6,890-image validation split. Full paired predictions are not released.
- The paper calls McNemar `p = 1.0` against Control-S “statistical
  equivalence.” McNemar's equality test can report no detected difference, but
  that is not an equivalence test: no practical-equivalence margin or
  corresponding equivalence/noninferiority design is specified. We therefore
  report paired differences and tests without converting a large p-value into
  proof of equivalence.
- The modern package's built-in exact McNemar helper overflows on some
  full-validation comparisons because it converts enormous binomial
  coefficients directly to binary64. This does not show that the paper's
  historical p-value is wrong—the canonical notebook can delegate to
  statsmodels—but it prevents end-to-end reproduction through the advertised
  helper. Our analyzer keeps the package contingency table and uses SciPy's
  stable exact binomial test, verified against the package on 2,601 small-count
  cases.
- The released SPRKD checkpoint scores about 81.64% on the validation indices
  serialized inside that checkpoint under the recovered preprocessing, while
  the separate historical 500-epoch metric trace reconstructs to 94.543%
  sample-weighted final accuracy (95.007% best epoch). The historical Control-S
  trace reconstructs to 95.399% final (95.747% best), so that released run has
  Control-S above SPRKD even though Table 1 reports the reverse ordering. The
  checkpoint, trace, and table therefore do not identify one common trained
  run/state.
- The historical SPRKD and Control traces each contain 500 x 108 validation
  minibatches. The release helper samples them at stride 323 (training steps per
  epoch), which selects individual validation minibatches rather than epoch
  summaries. The executed release notebook consequently labels single-batch
  values (96.88% and 93.75%) as final epoch accuracies.
- The released 500-epoch Hessian artifacts contain traces of 54.96 (SPRKD),
  35.48 (Control-S), and 209.47 (RKD), whereas Table 1 reports 33.39, 71.33,
  and 408.27. RKD remains the largest in both sources, but the released
  SPRKD/Control-S ordering is reversed: the artifact has a lower trace for
  Control-S. The repository's test asserts only that RKD is largest, so it does
  not expose this discrepancy. Hessian estimates can depend on stochastic
  probes and exact model/data states; because those provenance details are not
  fully recoverable, this is reported as an artifact-to-paper mismatch rather
  than evidence that either calculation is intrinsically wrong.

These observations are evidence about the release bundle, not accusations
about intent. Scratch results are evaluated independently under the frozen
protocol.
