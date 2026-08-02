Paper: https://arxiv.org/abs/2607.17674v1

Registered as: https://github.com/Atlas3DSS/nulspec/issues/25

Source: https://github.com/Awni00/latent-strategies-in-lms at
`0c0f221d7dc37cd4eb7fb1af3332520bccf4d9fe`

## Claim to test

Figure 3 reports that a model-directed global-plus-token factorization of
benchmark-adapted Qwen2.5 0.5B and 1.5B preserves approximately 0.99
Distributional Fidelity while reaching approximately 0.91 cross-input Strategy
Alignment / Analogical Consistency, substantially above ELBO-style baselines.

## Why an independent result helps

The method is a potentially useful way to expose and intervene on latent
reasoning strategies. The paper is recent, the benchmark is computational,
and the code is small enough for an independent local attempt. Confirmation,
failure to reproduce, and an execution failure would all clarify how much of
the headline result is recoverable from the public release.

## Scope and public-artifact boundary

- Artifact verification first.
- Released-code reproduction for the two executable global-plus-token Qwen
  configs.
- Separate manuscript-method arms because the paper specifies model-sampled
  factorization responses while the released config uses benchmark responses.
- No reconstructed six-method or 504-run grid until missing beta/schedule and
  architecture choices are prospectively resolved.

## Constraints

- Local RTX 4090 24 GB, RTX 3090 24 GB, and RTX PRO 6000 Blackwell 96 GB are
  available, but unrelated services remain untouched and every shared-host job
  is resource-capped.
- Released model/data checkpoints and raw result tables are absent.
- Paper Figure 3 values must initially be digitized from the plot.
- The single disclosed seed does not identify fresh-training variance.

Protocol: `protocols/2607.17674/REPRODUCTION_PROTOCOL.md`

The nominator has no disclosed conflict of interest with the paper authors.
