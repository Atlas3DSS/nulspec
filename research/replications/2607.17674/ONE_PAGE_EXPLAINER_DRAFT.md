# Can a language model reveal which reasoning strategy it is using?

*Results-pending explainer for “Uncovering Latent Reasoning Strategies in
Language Models” (arXiv:2607.17674v1). This draft must not be published as a
replication verdict until the registered runs and review hierarchy finish.*

Language models can reach the same answer in genuinely different ways. They
might add a list from left to right, combine pairs, or work backward; solve an
equation by subtracting first or dividing first; convert a number directly or
through binary. The visible answer does not tell us whether the model has a
stable internal representation of those choices—or whether we can select and
reuse one choice on a new problem.

The paper proposes turning that hidden choice into an explicit continuous
variable, `z`. A **router** reads a problem and samples `z`. A **generator**
reads the problem plus `z` and produces the solution. During training, a third
network sees the complete problem and solution and helps infer which `z` could
have produced it. All three roles start from a fitted Qwen2.5 model, and the two
trainable backbones use small LoRA adaptations rather than full retraining.

The clever part is the loss. A conventional variational objective can learn to
ignore `z`: the generator already knows how to solve the task, so it can keep
producing good answers while the supposed strategy variable carries nothing.
The authors instead give more reconstruction weight to tokens that surprised
the frozen base model. Those high-surprisal positions are often where a
solution commits to one strategy rather than another. Their headline result is
that this “model-directed” pressure preserves valid behavior while making the
same sampled latent transfer a consistent strategy between related problems.

We are testing that claim on the authors’ six-family synthetic benchmark with
their released Qwen2.5-0.5B and 1.5B recipes. The public artifacts do not permit
a literal recreation of every figure: raw results, checkpoints, exact tables,
the full method grid, and run-to-run variance are absent. We therefore froze
four defensible primary arms before seeing results. Track R runs the released
config; Track M changes only the response source to match the manuscript. That
separation matters because the manuscript trains on responses sampled from the
fitted model, while the released paper config trains on benchmark responses.

Our pre-result code audit found two additional details worth testing, not
hiding. First, the released trainer reconstructs the latent closing marker
`</z>` as one extra token even though the equation sums over response tokens.
That changes the reference-loss normalization by about 3.2% on average in the
frozen training set; whether it changes the final scientific conclusion is not
yet known. Second, model-response sampling and final fidelity evaluation
restart the same random-number stream in each batch. Individual samples still
have the intended marginal distribution, but outcomes across batches are not
independent and naive uncertainty intervals would be misleading.

We will preserve those behaviors in the faithful code run. We also froze a
separate, trace-preserving evaluator before any primary metric existed. It
records all 10,000 fidelity outcomes and 1,024 latent-transfer pairs, first
replays the released scalar exactly, and then advances one random stream as a
labeled sensitivity. Corrections never replace the primary observation.

The eventual verdict will answer three separate questions: **Did the released
recipe run? Did its numbers land near the approximate published bars? Does the
manuscript’s model-sampled method support the same qualitative claim?** A null
result, a failed run, or a sensitivity to one hidden implementation choice is
still useful if every input, error, trace, and limitation is preserved well
enough for someone else to check.
