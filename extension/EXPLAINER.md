# Beyond Perplexity: when does small-model PPO actually work?

The [original paper](https://arxiv.org/abs/2607.25091) argues that useful
reinforcement learning for small language models requires a fluent supervised
model—roughly, SFT perplexity below 20—and an informative reward model. Our
reproduction supports the capacity pattern but finds that the stronger rule is
not yet predictive. Pythia-70M produced no
reliable gain and suffered severe numerical instability, as expected from its
high perplexity. Pythia-410M reproduced the paper's positive *release-style*
reward delta, but neither its exact-code nor paper-faithful rerun improved under
a seeded, same-prompt paired evaluation. The released definition of
"informative reward" is also not a measurable pre-PPO gate, and the policy is
evaluated with the same reward model that trained it.

## Proposed extension

We test a three-gate theory of small-model RL:

1. **Language headroom.** The SFT policy must already generate coherent text.
   Reference-text perplexity is retained as an imperfect but useful proxy.
2. **Reward validity.** Before PPO, the reward model must separate held-out
   chosen/rejected pairs with useful margin *and* transfer to SFT-generated,
   controlled-degradation probes labeled by an independent evaluator. It must
   remain calibrated and produce numerically invariant scores.
3. **Numerical integrity.** PPO updates must remain finite and recover
   transactionally: weights and optimizer moments are restored together after
   a failed update, while RNG provenance is logged so the retry is auditable.

This separates three questions the release currently blends together: did PPO
survive, did it increase its own training reward, and did it improve output
quality under an independent evaluator?

## Primary experiment

The boundary study uses Pythia-70M, 160M, and 410M on the exact released
TinyStories data. Each model is trained with seeds 42, 123, and 777 under two
conditions:

- **Release:** the exact released reward initialization, bfloat16 PPO reward
  inference, and weights-only rollback.
- **Paper-faithful:** merge the SFT adapter before attaching reward LoRA, use
  float32 reward inference, and reset optimizer moments after rollback.

This is an 18-arm matrix. Exact and paper-faithful arms for a given model/seed
share the same SFT checkpoint. The workstation RTX 4090 is assigned 70M/160M;
the dev-box RTX PRO 6000 is assigned 410M under the existing CPU, memory,
nice/ionice, GPU-identity, and Palworld guardrails.

The primary endpoint is a blinded external preference judgment, not the
training reward. Qwen 27B receives the same prompt and the SFT/PPO continuations
in both A/B orders. A pair counts only when both orders map to the same winner;
position-inconsistent judgments are reported separately. The judge is first
calibrated on held-out released chosen/rejected pairs. We report paired win
rates, bootstrap intervals, sign tests, position bias, diversity, perplexity,
training-reward delta, PPO warning counts, and rollback outcomes. A post-PPO
audit also compares each training-reward direction with Qwen's
position-consistent preference, directly exposing reward hacking or
off-distribution reward failure. Every prompt, continuation, orientation, raw
response, and parsed decision is retained.

Qwen is not treated as an oracle. A final **outer teacher** audits the reviewer,
but it is separated by a one-way boundary: it can read only Qwen's structured
review records—not the small policies, their checkpoints, prompts,
continuations, rewards, or training state. It checks order consistency,
winner/rationale contradictions, vacuous reasoning, and visible position bias.
Its flags cannot become training reward or silently change the primary result.
The initial teacher is Codex using the already authenticated ChatGPT
subscription; a paid-per-token Fable adapter is deliberately left disabled.
This strict view cannot determine whether an unseen story preference was
semantically correct, but it can detect whether Qwen behaved like a reliable
review process. That is the intended “review the reviewer” role.

## Prospective test

Before PPO, each arm emits a readiness vector: SFT perplexity, held-out reward
accuracy, chosen/rejected margin distribution, Bradley–Terry probability/Brier
score, and FP32/BF16 batch-shape sensitivity. A readiness rule is fit only on a
development subset and then tested on held-out model/seed arms. Success requires
the lower confidence bound of independently judged PPO preference to exceed
chance without a numerical-failure stop.

The key falsifiable claim is therefore:

> Low perplexity is necessary but not sufficient; independent reward validity
> and numerical integrity prospectively identify the small policies that
> benefit from PPO.

If the readiness vector predicts held-out gains, this upgrades a retrospective
observation into a usable decision rule. If it fails, the negative result is
still meaningful: it shows that the paper's available pre-PPO diagnostics
cannot determine when its costly RL stage should be run.
