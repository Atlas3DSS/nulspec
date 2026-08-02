# External peer-review ledger

Every provider request is retained, including zero-cost transport failures and
an ineligible extra call. The exact raw traces remain in the ignored immutable
lab archive. `results/external_review_training_traces.jsonl` is the sanitized,
public, training-ready projection; hashes and byte counts bind it to the exact
private originals.

## Accounting

- Anthropic/Fable: **$3.224742**
- OpenRouter/GLM+Kimi: **$1.21702032**
- Total external-review cost: **$4.44176232**
- Provider request events: **6**
- Actual model invocations: **4**
- Consensus-eligible invocations: **2**

| Event | Provider | Model | Validation | Validated verdict | Cost |
|---|---|---|---|---|---:|
| `FABLE-REFUSAL-20260801-001` | Anthropic | `claude-fable-5` | technical_hard_fail | — | $3.22474200 |
| `OR-TRANSPORT-20260801-001` | OpenRouter | `z-ai/glm-5.2-20260616` | completed_invalid | — | $0.00000000 |
| `OR-TRANSPORT-20260801-002` | OpenRouter | `moonshotai/kimi-k3-20260715` | completed_invalid | — | $0.00000000 |
| `OR-REVIEW-20260801-001` | OpenRouter | `z-ai/glm-5.2-20260616` | completed_invalid | — | $0.04710276 |
| `OR-REVIEW-20260801-002` | OpenRouter | `moonshotai/kimi-k3-20260715` | completed_invalid | — | $1.12317300 |
| `OR-REVIEW-20260801-003` | OpenRouter | `z-ai/glm-5.2-20260616` | completed_valid | PASS | $0.04674456 |

## Release consequence

The permitted GLM/Kimi pair did not produce two valid structured PASS
decisions. GLM's raw content declared PASS but paired it with the FAIL-only next
step; Kimi's raw content declared PASS but ended at the output limit before the
JSON completed. The later valid GLM recovery is retained and billed but cannot
count. The supplemental decision is therefore **HARD_FAIL** and
publication remains blocked for human review. No external review can authorize
author-email dispatch; that always requires separate approval of the exact
hashed draft.
