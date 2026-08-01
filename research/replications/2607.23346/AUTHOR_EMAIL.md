# Draft author email — not sent

Dispatch always requires final human approval. A Fable `PASS`, or closure of
all three actions from a normal `FAIL`, can make this exact draft eligible for
that approval but cannot authorize or send it. A `HARD_FAIL` also stops the
publication workflow for human review.

**Subject:** Independent replication attempt of the SPRKD malaria experiment

Hello SPRKD authors,

We are a small independent replication team, and this is our first public
end-to-end replication. We attempted the five-trial, 500-epoch malaria result
from arXiv:2607.23346 using the paper-linked repository at commit
`7f1655ff1295c9a6dcf8d24f6410a036cd7e3497`.

We separated three kinds of evidence rather than choosing whichever result was
closest to Table 1: replay of the released artifacts, the exact current public
reproduction path, and a narrow paper-intent reconstruction that starts SPRKD
from fresh parameters and keeps the response-KD teacher at its saved two-epoch
state. We retained all five seeds, final and best histories, paired predictions,
source/config hashes, and every failed command.

Our frozen final-epoch result did not reproduce Table 1. The exact current
script path averaged 85.74% SPRKD accuracy (SD 20.01; one chance-level final),
and the narrow paper-intent path averaged 67.98% (SD 24.63; three chance-level
finals), versus 71.51% for response KD from the unmodified weak teacher. At the
same time, every SPRKD run reached at least 92.61% during training, and the
exact path's five-run best-epoch mean was 94.83%. We therefore classify the
public final-result replication as not reproduced while treating the intended
method itself as inconclusive, not disproved. The best/final contrast makes the
historical checkpoint-selection and failed-run policy especially important.

One outcome-motivated diagnostic may help reconcile intent. Replacing only the
student's terminal Softmax with identity so supervised cross-entropy receives
logits produced five stable SPRKD finals averaging 94.792% (SD 0.193), almost
exactly Table 1, while the paired scratch controls averaged 95.152%. No
corrected SPRKD optimizer recorded a negative-Hessian eigenstep. We do not use
this post-hoc result to rewrite the frozen classification, but it makes the
historical loss input especially valuable to clarify.

Several public artifacts and implementation details appear not to identify the
same historical run. In particular, the modern script directly initializes the
student at the ASR and mutates the teacher later used for response KD; the
preserved traces, checkpoints, Hessian files, and Table 1 also give different
values or orderings. We may still have misunderstood the intended historical
configuration.

Would you be willing to share or clarify any of the following?

- the exact code revision, environment, seeds, and per-trial results behind
  Table 1;
- whether reported accuracies are final-epoch or selected checkpoints;
- whether supervised cross-entropy received logits or terminal-Softmax
  probabilities;
- whether SPRKD began randomly or directly from the ASR, and whether ASR used
  the lowest-loss or last recorded saddle;
- whether response KD used the untouched weak teacher or the ASR-mutated
  teacher, and whether its loss received logits; and
- the model states, data, and stochastic settings behind the reported Hessian
  traces and McNemar tests.

Our longer question list and complete methods are in the draft public record.
We would be glad to freeze and run a clarified author-intent configuration,
publish your response alongside our report, and correct anything we have
described inaccurately.

Because this is our first replication, we would also genuinely value feedback
on how our process or presentation could be more useful, fair, and efficient
for authors and future replicators. The aim is not embarrassment; it is a clean,
repeatable record that helps the community learn faster.

Best,

The NULSPEC team
