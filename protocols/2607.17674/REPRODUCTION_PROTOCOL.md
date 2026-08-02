# Frozen reproduction protocol: arXiv:2607.17674

**Protocol version:** 1.0.0

**Status:** frozen for the public-artifact primary matrix after commit and tag
`2607.17674-protocol-v1.0.0`

**Target:** *Uncovering Latent Reasoning Strategies in Language Models*

**Paper:** <https://arxiv.org/abs/2607.17674v1>

**Upstream code:** <https://github.com/Awni00/latent-strategies-in-lms>

**Upstream revision:** `0c0f221d7dc37cd4eb7fb1af3332520bccf4d9fe`

No primary GPU arm may begin until this protocol, `config.json`, and
`matrix.csv` pass validation, are committed, and are tagged
`2607.17674-protocol-v1.0.0`.

## 1. Question and claim under test

The primary question is whether an independent execution of the public
artifacts supports the paper's headline pretrained-model result: a
model-directed global-plus-token reconstruction objective can preserve the
base model's response distribution while recovering a latent variable whose
strategy meaning is consistent across related inputs.

The paper's main pretrained comparison (Figure 3 in arXiv v1) visually reports
approximately 0.99 Distributional Fidelity and 0.91 Strategy Alignment for the
global-plus-token objective on both Qwen2.5 0.5B and Qwen2.5 1.5B. The figure
visually reports roughly 0.34--0.35 Strategy Alignment for ELBO-style
baselines. These values are plot digitizations, not author-released numerical
records.

## 2. Ordered study phases

The study follows this order:

1. verify the paper, source, configuration, model, and environment artifacts;
2. execute the exact released-config track;
3. execute the manuscript-method track where it differs;
4. freeze primary observations and their interpretation;
5. only then run reconstructed figure arms, added seeds, corrections, or other
   extensions under a new protocol version.

A failed arm remains a result. A repaired arm receives a new ID and never
overwrites the failure.

## 3. Public-artifact boundary

The repository provides executable paper configurations for:

- benchmark generation;
- LoRA adaptation of Qwen2.5 0.5B and 1.5B on the multi-task benchmark;
- one global-plus-token factorization with `beta = 0.01`, full-training linear
  beta warmup, and `response_source = benchmark`;
- evaluation on 1,024 prompt pairs.

The release does **not** provide raw reported results, trained checkpoints,
per-arm numerical tables, figure-generation code, the exact pretrained
beta/schedule selection for every bar, multiple training seeds, or the
complete 504-run random-initialization configuration grid. The README calls
the provided configurations “starting points” and states that they do not
specify every reported experiment.

Accordingly, version 1.0.0 freezes only settings that can be obtained without
inventing missing choices. A later figure-reconstruction protocol may be
added after author clarification or an explicit, prospective ambiguity rule.

## 4. Source conflict and separate tracks

The manuscript repeatedly states that factorization responses are sampled
from the frozen fitted model,
`x ~ D_X, y ~ p_theta(.|x)`. Appendix Table 1 says this applies to all
model-directed variants. The released paper factorization config instead sets
`response_source` to `benchmark`.

The README explains that the fitted model reaches near-zero cross-entropy and
therefore argues `p_theta` is approximately the benchmark distribution. That
argument does not make the two executable data-generation procedures
identical. We therefore keep them separate:

- **Track R — released config:** `response_source = benchmark`.
- **Track M — manuscript method:** `response_source = base-model`; all other
  disclosed settings remain equal to Track R.

Neither track is treated as the hidden recipe that produced Figure 3. Track R
tests the shipped recipe. Track M tests the written sampling method.

## 5. Frozen primary matrix

`matrix.csv` registers four primary arms, all using seed 314159:

- Track R and Track M for Qwen2.5 0.5B;
- Track R and Track M for Qwen2.5 1.5B.

The exact released benchmark, base-model, factorization, and evaluation
configuration hashes are in `SOURCE_MANIFEST.json`. Track M changes only the
factorization response source and its output paths. Base-model checkpoints are
reused across R and M for a given model size so the source conflict is isolated
from stochastic base adaptation.

## 6. Models and immutable revisions

The model repositories and revisions are:

- `Qwen/Qwen2.5-0.5B` at
  `060db6499f32faf8b98477b0a26969ef7d8b9987`;
- `Qwen/Qwen2.5-1.5B` at
  `8faed761d45a263340a0528343f099c05c9a4323`.

Each snapshot is downloaded by revision into an immutable local directory.
The base-model command overrides `pretrained_name_or_path` with that directory
and runs with the Hub offline. This is a provenance-only override of the
mutable model name in the released JSON; it does not change model content.
Downloaded file sizes and SHA-256 digests are captured before training.

## 7. Benchmark and training

The released benchmark uses seed 314159. Each of six individual task datasets
and the combined multi-task dataset contain 100,000 training, 10,000
validation, and 10,000 test records. Benchmark configuration and generated
Parquet hashes are recorded.

For each base model, the released recipe uses:

- one training epoch;
- effective batch size 128 and micro-batch size 8;
- LoRA rank 16, alpha 32, and dropout 0;
- AdamW learning rate 2e-4, zero weight decay;
- 10% warmup followed by cosine decay to 10% of peak LR;
- seed 314159.

The factorizer uses:

- continuous latent dimension 64;
- `model_directed` reconstruction, `alpha = 0.05`, `gamma = 0.25`;
- `beta = 0.01` with linear warmup over 100% of training;
- one epoch, effective batch 128, micro-batch 8;
- LoRA rank 16, alpha 32, dropout 0;
- learning rate 2e-4 and weight decay 0.01;
- bfloat16 and seed 314159.

No automatic batch-size, precision, optimizer, epoch, or stopping adjustment
is permitted in a primary arm. A resource failure is preserved and any
modified attempt requires an amendment and new arm ID.

## 8. Evaluation and uncertainty

The primary evaluation is the released evaluator with 1,024 prompt pairs,
batch size 128, and seed 314159. It reports:

- Distributional Fidelity: fraction of router-sampled generations compatible
  with at least one benchmark strategy;
- Strategy Alignment / Analogical Consistency: fraction of paired related
  inputs for which generations conditioned on the same sampled latent share a
  compatible strategy.

The exact released metrics are preserved first. We additionally report a
deterministic nonparametric 95% bootstrap interval over the 1,024 retained
pairs where per-pair records permit it, plus per-task values and counts.

That interval measures conditional evaluation-pair uncertainty for one trained
checkpoint and one decoding realization. It does **not** measure
fresh-training or fresh-decoding variability. Because the paper releases one
seed and no run-to-run intervals, primary training variance is not identifiable
from public artifacts. Additional seeds are an extension and cannot alter the
primary observation.

## 9. Comparison rules

Execution, numerical agreement, and claim support are judged separately.

- **Execution fidelity:** exact pinned sources and settings completed without
  a semantic patch.
- **Close numerical reproduction:** both digitized Figure 3 metrics are within
  0.03 absolute of the corresponding bar. The tolerance is prospective and
  reflects figure digitization plus a single stochastic evaluation; it is not
  a claim about statistical equivalence.
- **Directional agreement:** Distributional Fidelity is at least 0.95 and
  Strategy Alignment is at least 0.80 for global-plus-token.
- **Headline comparative support:** cannot be classified from the four-arm
  v1.0.0 matrix alone because the public release does not fully specify the
  ELBO and other Figure 3 arms. It requires a frozen figure-reconstruction
  matrix.

Possible study-level conclusions are: supported within tested scope, mixed,
not reproduced, contradicted, or inconclusive. Failure to reproduce is not
treated as proof that the paper's claim is false.

## 10. Code, environment, and deviations

The upstream `uv.lock` is authoritative and is installed with
`uv sync --frozen`. Package resolution, Python, PyTorch, CUDA runtime, driver,
kernel, CPU, RAM, and GPU model are captured. The first attempt uses upstream
code without patches.

Any import, compatibility, or runtime failure is preserved before a fix is
considered. A non-semantic compatibility fix is a new attempt under an amended
protocol; a change to data, objective, precision, optimization, or evaluation
creates a distinct track.

Errors attributable to our operation are recorded separately from limitations
or failures attributable to the paper or released artifacts. Neither category
is deleted after correction.

## 11. Workload safety

Only one NULSPEC experimental GPU workload may run on a host at a time. Every
launch binds an exact GPU UUID in its private manifest and applies a cgroup
memory high-water mark, hard memory cap, CPU quota, low scheduling priority,
I/O priority, and minimum-free-RAM preflight.

Unrelated services and processes are outside scope: they are not stopped,
signalled, reconfigured, inspected for content, or placed in the experiment's
cgroup. If GPU, RAM, thermal, or pressure guards activate, the experiment
stops. The guard is never relaxed automatically.

## 12. Stopping and amendments

An arm stops only on normal completion, a non-finite state the released code
cannot recover from, a resource guard, or an operator interruption recorded in
the run manifest. Null or unfavorable metrics are not stopping criteria.

After the protocol tag exists, this file is immutable. Clarifications,
reconstructed comparison arms, additional seeds, performance optimizations,
and fixes require a numbered amendment and new protocol tag.
