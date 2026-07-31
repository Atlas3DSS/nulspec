# Full-matrix result in one page

## Verdict

**Bottom line:** We broadly reproduced the released numerical table, but did
not confirm the paper's stronger claims of universal stable convergence or a
robust capacity-headroom rule; actual output-quality improvement remains
unresolved. The appropriate overall classification is **partially reproduced**,
not confirmed, refuted, or wholly inconclusive.

We completed all 30 protocol-registered model-by-corpus arms: 15 exact
released-code runs (Track R) and 15 runs of the operations stated in the
manuscript but absent from the default release path (Track M). Every selected
arm is claim-ready, every failed attempt is retained, and all eight
compatibility-trained checkpoints that required it were reevaluated on the
exact paper software stack.

Track R reproduced the paper's aggregate reward delta within our conditional
95% prompt interval for 12 of 15 configurations. That is meaningful numerical
agreement, but it is weaker evidence than “12 successful independent
replications”: each arm has one training seed and one sampled continuation per
prompt. Ten of 15 directional assessments were inconclusive, four agreed with
the published direction, one disagreed, and only SmolLM2-360M/WikiText remained
significant under the deterministic paired endpoint after Holm correction
across all 15 arms.

## What changed under the manuscript-stated method

Track M reuses each matching Track R SFT checkpoint, then bundles three
paper-stated operations: initialize reward training from the SFT-merged model,
run PPO reward inference in float32, and reset optimizer moments after a
rollback. It is a method-bundle test; this design cannot identify which
component caused a change.

The bundle changed both stability and measured outcomes:

- Full-budget completion improved from 11/15 in Track R to 12/15 in Track M.
  Pythia-70M/TinyStories went from a five-rollback stop at step 35 to all 250
  steps with one recovered corruption. The three Pythia-160M arms survived 47,
  43, and 84 additional recorded steps, but all still exhausted the unchanged
  five-rollback limit. Total corruption events fell from 20 to 16. Raw warning
  totals were higher while total PPO exposure was longer; exposure-normalized
  warning rates were mixed and are reported per arm.
- Only 5/15 published deltas fell inside the Track M conditional prompt
  intervals. Eleven directional assessments were inconclusive, three agreed,
  and one disagreed. The deterministic paired endpoint found six positive arms
  after within-track Holm correction, compared with one in Track R. These are
  internal reward-model results, not six independently established
  improvements in human-perceived output quality: the tracks train different
  reward models and therefore do not share a calibrated score scale.
- The release's stated necessary-condition observation—material reward gains
  occur only when SFT perplexity is below 20—held in Track R but not in Track
  M. Three Track M arms had release-style deltas above +0.2 despite SFT
  perplexity at or above 20; two remained above +0.2 under the deterministic
  paired endpoint. This shows that the observation is not invariant to the
  manuscript-method bundle in these single-seed runs. It does not test the
  paper's full capacity hypothesis because the release does not operationalize
  or retain a claim-level measure of reward-signal informativeness.

The largest qualitative reversal is Pythia-410M/WikiText: the paper reports
−1.0429, while Track M gives +1.6959
[+1.0325, +2.3337] release-style and +1.7139
[+1.1029, +2.3391] deterministic paired. Conversely,
Pythia-410M/TinyStories loses its published positive release-style result in
Track M, whose interval crosses zero. These contrasts make the
manuscript/release mismatch scientifically consequential, while the
single-seed and reward-calibration limits prevent causal attribution.

## What we can and cannot conclude

The claims separate cleanly:

- **Released numerical results — broadly reproduced.** Track R placed 12/15
  published reward deltas inside the conditional prompt intervals, although
  most directional effects remained inconclusive and three configurations
  missed.
- **Universal stable convergence — not confirmed.** The prescribed PPO budget
  was reached in 11/15 Track R arms and 12/15 Track M arms. In both
  interpretations, some configurations repeatedly exhausted the released
  rollback policy.
- **Capacity-headroom rule — only narrowly reproduced, not shown robust.** The
  paper's explicit PPL-based necessary condition held in Track R and failed in
  Track M. The stronger joint claim cannot be fully tested because reward-signal
  informativeness was neither operationalized nor retained at claim level.
- **Actual output-quality improvement — unresolved.** The available endpoints
  score each policy with its own reward model, and the independent Qwen review
  failed its outer-teacher reliability audit.

We can therefore conclude that the released pipeline is numerically unstable
in a configuration-dependent way, that most published aggregate deltas are
compatible with our released-code reruns under conditional prompt uncertainty,
and that implementing the manuscript-stated method bundle changes the result
landscape. We cannot estimate training-to-training or decoding-to-decoding
variance, claim practical equivalence when an interval contains zero, attribute
Track M to one correction, or infer general output quality from an arm's own
reward model.

The blinded Qwen reviewer extension does not close that last gap: its
outer-teacher audit found substantial position sensitivity, so Qwen is
published as a fallible diagnostic rather than an oracle. Blackwell-native
sampled evaluations also changed under fresh unseeded decoding; claim values
therefore come only from exact-stack Ampere/Ada reevaluation. Deterministic
native-to-exact endpoint shifts were at most 0.0064 for the final Track M
checks, supporting evaluation-stack sensitivity as small without asserting
that Blackwell and exact-stack training are equivalent.

## Reproduce or audit it

The generated [full report](FULL_MATRIX_REPORT.md) contains every arm,
conditional interval, Holm-adjusted result, integrity signal, fixed
Track M-minus-R contrast, and variance limitation. The
[machine-readable analysis](full_matrix_analysis.json),
[Track M runtime audit](TRACK_M_RUNTIME_EVENT_AUDIT.md), and separate
[error ledger](../docs/ERROR_LEDGER.md) distinguish target-work findings from
our own mistakes. The Track M inventory binds 1,491 selected-attempt files
totalling 31,583,533,446 bytes; checkpoints remain outside ordinary Git
history under the repository's artifact policy.

Candidate follow-ups are explicitly separated into replication-strengthening
work, robustness replication, and new extensions in the
[extension roadmap](../docs/EXTENSION_ROADMAP.md). None changes this frozen
primary verdict.
