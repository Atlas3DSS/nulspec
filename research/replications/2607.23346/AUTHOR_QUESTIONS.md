# Questions for the authors

These are intended as a constructive request for provenance, not an allegation.
Answers or additional artifacts would let us tighten the replication and amend
the public record quickly.

1. Which code revision and environment produced each of the five malaria trials
   summarized in Table 1? Are the per-seed metrics/checkpoints still available?
2. Did those SPRKD students begin from fresh random parameters and approach the
   injected ASR iteratively, or begin directly at the ASR as the modern
   reproduction script does?
3. Was each ASR built from the last recorded saddle or the minimum recorded-loss
   saddle for each teacher? If minimum-loss, were losses evaluated on a common
   batch/dataset before comparison?
4. Which saddle rule, epsilon, transformation weight, stagnation threshold,
   NHE mode, and PGD/reversion behavior were active in the Table 1 runs?
5. For RKD, was the teacher the saved two-epoch weak teacher or teacher 0 after
   ASR injection? Did the loss receive pre-Softmax logits or already-softmaxed
   model outputs?
6. Are Table 1 accuracies final-epoch or selected best-checkpoint values, and
   were validation batches sample-weighted? How were the 175 Figure 3
   checkpoints selected from 500 epochs?
7. Could the full paired predictions or contingency tables used for the
   reported McNemar tests be released?
8. Can you share the five trial seeds and package versions, especially Torch,
   CUDA, fastai, PyHessian, and `hessian-eigenthings`?
9. Which model states, validation samples, stochastic probes, and analysis
   settings produced Table 1's Hessian traces? The released 500-epoch artifacts
   contain different trace values and reverse the SPRKD/Control-S ordering.
10. For supervised malaria training, did `CrossEntropyLoss` receive final-layer
    logits or the current architectures' terminal-Softmax probabilities? Were
    failed late-training runs retained in the five-trial average, or was a best
    checkpoint selected?
11. Was the malaria split grouped by patient in the historical runs, or was it
    the released random image-level split? If grouped, can the patient IDs or
    split manifest be shared?

We would be glad to add an author response, rerun a clarified configuration,
and credit any correction. Null results and corrections are both useful; the
goal is to make the work easier for the next independent team to reproduce.
