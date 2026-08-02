# Paper-to-code implementation audit: arXiv:2607.17674v1

## Scope and evidentiary status

This audit compares the arXiv v1 TeX source with the immutable upstream tree at
commit `0c0f221d7dc37cd4eb7fb1af3332520bccf4d9fe`. It was performed while the
first preregistered primary arm was still running. It therefore records code
behavior and interpretation constraints, not experimental outcomes.

The released implementation remains untouched in every primary run. A code
behavior described below is not called an error merely because the paper omits
it. We distinguish exact mappings, release-only implementation details, and
confirmed paper/code differences. Any proposed correction is reserved for a
separately labeled extension.

## Direct paper-to-code mappings

| Paper method | Released implementation | Audit assessment |
| --- | --- | --- |
| A frozen fitted language model defines the target distribution | The trained base export is loaded independently for the adapted models and, when needed, as a frozen evaluation-mode reference | Direct mapping |
| The router and generator share parameters \(\phi\) | One `router_generator_model` supplies both the final router state and latent-conditioned token logits | Direct mapping |
| The posterior \(q_\xi(z\mid x,y)\) is separate and training-only | A second base-initialized backbone plus posterior heads reads the full framed input-response sequence | Direct mapping |
| Router and posterior are diagonal Gaussians | Separate linear mean and log-variance heads are used, with one reparameterized posterior sample per example | Direct mapping; the `[-8, 8]` log-variance clamp is a release-only stability detail |
| A sampled latent is projected to a pseudo-token embedding | A learned linear projection of \(z\) is added at the `<z_empty>` placeholder position | Compatible parameterization; the additive placeholder embedding is not specified in the manuscript |
| Models are lightweight LoRA adaptations initialized from the fitted base | Both backbones receive rank-16, alpha-32 LoRA adapters on attention and MLP projections; only the added structural-token rows are sparsely trainable | Direct mapping to the released configs |
| Negative conditional ELBO uses \(\mathrm{KL}(q\Vert r)\) | The analytic diagonal-Gaussian implementation computes `KL(posterior || router)` and sums latent dimensions before the batch mean | Direct mapping |
| Model-directed reconstruction uses base surprisal, normalized token weights, \(\kappa\), and \(c_\theta\) | The implementation computes frozen-base per-token NLL, applies exponent \(\gamma\), normalizes per response, applies the \(\kappa\) scale correction, mixes uniform and directed pressure with \(\alpha\), and divides by a validation estimate of \(c_\theta\) | Direct mapping apart from the boundary-token issue below |
| Full linear warm-up of \(\beta\) | With 782 optimizer steps, `100%` resolves to 782 and the first step uses \(\beta/782\), reaching the target on the final step | Direct mapping |
| Distributional Fidelity is the fraction of strategy-compatible solutions | The evaluator counts unique-strategy and ambiguous-strategy valid outcomes and divides by all 10,000 test inputs | Direct mapping |
| Analogical Consistency transfers one router sample between distinct inputs in the same task family | The evaluator samples 1,024 distinct within-family pairs, generates twice with the same sampled latent, and tests strategy agreement | Direct mapping, with the ambiguity convention below |

## Confirmed interpretation-relevant differences and hidden choices

### 1. The released config does not use the manuscript response distribution

The manuscript repeatedly specifies factorization examples with
`y ~ p_theta(. | x)`. The released paper config sets `response_source` to
`benchmark`. This was already known before execution and is why the protocol
separates released-config Track R from manuscript-method Track M. Neither track
is allowed to stand in for the other.

### 2. Reconstruction supervision includes one latent-boundary token

The paper's reconstruction sum begins at the response tokens. In
`build_continuous_latent_conditioned_record`, the released code inserts
`<z> <z_empty> </z>` before the response but starts the supervision mask at
`</z>`, one position before the declared conditioned `y_span`.

A direct, read-only probe produced:

```text
input_ids              (..., <z>, <z_empty>, </z>, <y>, ...)
first_supervised_index                         ^
conditioned_y_start                                 ^
```

Consequently, the generator is trained to reconstruct `</z>` in addition to
the response. The frozen-base alignment gives this extra position zero
directed surprisal, but it still receives the uniform part of the released
global-plus-token objective (`alpha = 0.05`). It receives full uniform weight
under ELBO/global-scale objectives. The `c_theta` estimate excludes this token.

The consequence is not limited to one small token loss. The active-token count
inside the uniform average and the `base_loss` used to form `kappa` is
`T_y + 1`, while the `c_theta` reference uses `T_y`. In the frozen 100,000-row
training split, response-region lengths range from 12 to 121 tokens (median 32,
mean 36.86289), and the mean deterministic scale ratio `T_y / (T_y + 1)` is
0.967978. Thus the stated base-reference normalization is about 3.2% low on
average before accounting for the separately learned `</z>` prediction, with a
larger effect on short traces. This quantifies the objective-scale discrepancy;
it does not predict the eventual metric effect.

This is a confirmed code-to-equation difference. Its effect on learned metrics
is not known in advance, so the faithful primary retains it. A mask-corrected
paired rerun belongs in an extension and must not replace the released-code
result.

### 3. Released sampling helpers restart the same RNG stream for every batch

The standalone fidelity evaluator passes one fixed sampling seed into every
batch. Its generation helper calls `torch.manual_seed(seed)` at the start of
each call, so corresponding rows and decode positions in successive batches
reuse the same underlying random-number stream. Each individual draw remains
from the configured categorical distribution, but the 10,000 outcomes are not
independent conditional draws. This can alter realized Monte Carlo variance
and makes a naive independent-example interval inappropriate.

The same pattern is present earlier in Track M: model-sampled factorization
responses call the shared Hugging Face generation helper once per batch with
the same seed, and reuse that seed again for train, validation, and test splits.
Thus every response has the correct marginal sampling rule, but corresponding
batch rows across the 120,000 source prompts share random-number streams. This
is a released-code difference from the ordinary independent-sampling reading
of the manuscript algorithm.

The analogical evaluator does vary its seed by batch. Faithful primary arms
retain all released paths. Record-preserving, monotonically advanced RNG
sampling is an extension/sensitivity analysis for both Track M response
construction and final fidelity evaluation.

### 4. Ambiguous strategy agreement is implemented as set overlap

The manuscript writes Analogical Consistency as equality between inferred
strategies. The released validator can assign multiple compatible strategies,
and the evaluator counts a transferred pair as consistent whenever the two
strategy sets have a nonempty intersection. This is a reasonable operational
choice, but it is not stated in the paper and differs from literal equality if
ambiguous generations occur. The primary scalar follows released code; an
instrumented evaluation should report how many decisions depend on this rule.

### 5. Aggregate-only outputs prevent outcome-level auditing

The evaluator writes only the two final scalars. It does not retain the 10,000
fidelity classifications, the 1,024 pair classifications, task identifiers, or
generated responses. This does not change the primary calculations, but it
prevents direct auditing, task-conditioned intervals, ambiguity sensitivity,
and a faithful within-evaluation bootstrap from those artifacts.

## Audit-preserving execution policy

1. Run the released code and configuration without correcting any behavior
   above.
2. Report Track R and Track M separately, because they answer different
   fidelity questions.
3. Treat digitized Figure 3 bars as approximate references, not author data.
4. Mark uncertainty unavailable for aggregate-only primary evaluations.
5. After primary completion, run explicitly labeled sensitivities where
   resources permit: record-preserving evaluation, advancing-RNG evaluation,
   independent Track M response sampling, literal/set-overlap ambiguity
   comparison, and boundary-mask correction.
6. Report whether each sensitivity changes the substantive conclusion, even if
   the result is null.

## Current bottom line

The core mathematical proposal is recognizably and mostly directly implemented
in the released code. The response-source conflict is the largest known threat
to manuscript-faithful replication. The newly confirmed `</z>` supervision and
batchwise RNG restarts are narrower but scientifically relevant implementation
details. They do not invalidate the active run; they determine what that run
can honestly claim and define the most valuable paired extensions.
