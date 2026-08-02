# Author questions — draft only, do not send

**Release gate:** This is research correspondence, not an approved email. It
must wait for terminal analysis, the single final Fable decision, and exact
human approval of the recipient, subject, and body. No automated system may
send it.

**Proposed subject:** Questions from an independent replication of
arXiv:2607.17674

Hello Awni and John,

We are a small independent team attempting an end-to-end replication of
“Uncovering Latent Reasoning Strategies in Language Models.” Thank you for
releasing the benchmark and implementation; the compact CPU example and frozen
environment made it unusually practical to audit the full path before spending
GPU time.

Our registered runs are still in progress, so we are not asking you to react to
a verdict. We found a few places where your guidance could help us distinguish
the intended method from one particular released implementation:

1. The manuscript describes factorization training on responses sampled from
   the fitted base model, while `configs/paper/factorization.json` selects
   benchmark responses. Which source produced the pretrained Qwen results in
   Figure 3? We are running both as separate tracks rather than assuming they
   are interchangeable.
2. Could you share the exact pretrained run registry behind Figure 3—objective
   variant, beta, beta schedule, seed, and checkpoint/run-selection rule for
   each bar? The public config supplies one global-plus-token starting point,
   but we could not reconstruct the complete comparison grid or the distinction
   between the plotted ELBO and beta-ELBO categories.
3. In the released conditioned-record builder, the supervision mask begins at
   `</z>`, one token before the declared response span. Was reconstructing that
   delimiter intentional? Because the frozen-base reference assigns it zero
   directed surprisal while the active-token denominator includes it, the base
   normalization is about 3.2% lower on average for the released benchmark
   lengths. We are preserving this in the primary and reserving a response-only
   mask for a labeled sensitivity.
4. The shared generation helper resets one Torch seed for every batch. This
   affects both model-sampled training responses and standalone Distributional
   Fidelity evaluation; the analogical evaluator instead varies its seed by
   batch. Did the reported runs use these exact paths and batch sizes?
5. Analogical Consistency counts ambiguous generated strategies by nonempty set
   intersection, whereas the paper notation presents equality of one inferred
   strategy. Is set overlap the intended definition for the reported bars?
6. If available, raw metric tables, per-example outcomes, checkpoints, or
   plotting/run-selection code would let us make a much stronger comparison
   than digitizing Figure 3.
7. Could you share the accelerator model and approximate peak device-memory
   requirement for the pretrained arms? Our unchanged Qwen2.5-0.5B Track M
   attempt completed response generation but exceeded a 24 GB card while
   estimating `c_theta`, before the first factorization optimizer step. We do
   not infer that 24 GB was intended to be sufficient; the information would
   help other groups plan an exact run without a failed hardware-sizing trial.

We want to report these points plainly but constructively. If we have
misunderstood an intended convention, we would be grateful for the correction
and will preserve both our initial reading and the corrected analysis. We are
also very open to suggestions about what would make this replication more
useful to you or to others building on the work.

Best,

The NULSPEC team
