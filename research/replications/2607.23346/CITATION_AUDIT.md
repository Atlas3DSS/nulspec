# Citation-use audit

This audit asks a narrower question than the replication: does each cited
source support the particular statements for which SPRKD uses it? It does not
decide whether SPRKD's experimental conclusion is true, and `unverifiable`
does not mean false.

## Method

We extracted 47 unique bibliography entries and 146 citing-context blocks from
arXiv:2607.23346v1. Source identity was resolved deterministically before model
review. Of the 47 entries, 45 were exact matches and two remained unresolved;
the available evidence comprised 34 full texts, five official web sources,
three abstracts, three metadata-only records, and two failed acquisitions.

Every reference was reviewed by the same 26,895,998,464-parameter
Qwen3.6-27B Q4_K_XL GGUF, SHA-256
`ff6941ded525b34eb159496762c29dd0ec6e71dc31b74d57e75d871a03eec259`.
Thinking was disabled, temperature was zero, input packets and prompts were
hashed, and every response—including invalid and repaired attempts—was
retained. Jobs were physically routed across an RTX 3090 and RTX PRO 6000. A
Codex GPT-5.6 outer teacher, using the owner's monthly-plan authentication,
then reviewed every Qwen judgment against the supplied citing contexts and
source evidence. It could grade and correct the local reviewer but could not
alter a replication model or result.

The frozen 1–10 rubric treats unsupported confidence, invented evidence,
incorrect source identity, and materially wrong support verdicts as critical
errors. Source-retrieval failures are attributed separately from model-review
failures. This is deliberately stricter than checking whether a citation is
topically related.

## What happened

Qwen produced structurally valid primary reviews for all 47 references, but
only eight passed every mechanical evidence check without correction. The
outer teacher changed the support distribution substantially:

| Verdict | Qwen | Outer teacher |
|---|---:|---:|
| Supports | 30 | 6 |
| Partially supports | 8 | 25 |
| Overstated | 1 | 5 |
| Misattributed | 1 | 1 |
| Unverifiable | 7 | 10 |

Across the 45 model-evaluable cases, Qwen scored 7.02/10 on average (sample SD
1.59; median 7; bootstrap 95% interval for the mean 6.58–7.49). The teacher
flagged at least one critical error in 27/45 cases (60%). Consequently the
supervision-reduction gate remains closed: this local model is useful as a
first-pass reviewer, but its output is not reliable enough to publish without
outer review. Forty-six corrected cases are retained as potential supervised
training examples. The dominant targets are overconfident support verdicts
(22 primary cases) and evidence presented as verbatim despite being a
paraphrase or unsupported reconstruction (11 primary cases). The frozen
training actions are five accepts, 30 accepts-with-edit, 11 replacements, and
one exclusion caused by unavailable source evidence.

Most qualifications are not accusations of fabricated scholarship. A common
pattern is that a source supports the broad background claim but not every
narrower statement grouped into the same citation context. Ten cases remained
unverifiable under the evidence actually acquired. The item-level corrections
are published in
[results/CITATION_AUDIT_RESULTS.md](results/CITATION_AUDIT_RESULTS.md).

## Reproducibility and limits

Four blinded repeat jobs traversed the other production route. Source identity
and citation role agreed in 4/4, while the final verdict agreed in 2/4. Because
the repeated packet could have different batch neighbors and used a
route-dependent seed key, this measures route-level operational consistency,
not a causal GPU-hardware effect. A proper hardware test would use identical
singleton requests and a shared seed.

Raw Qwen and teacher traces are retained locally for error analysis and future
model improvement. To avoid republishing retrieved source text, the public
[JSON result](results/citation_audit_results.json) contains a per-batch SHA-256
inventory rather than the raw traces. The same JSON binds the source manifest,
Qwen run manifest, teacher run manifest, rubric, model file, and cross-route
comparison by digest. The bootstrap interval above describes this fixed set of
references; it is not a claim about performance on unseen papers.
