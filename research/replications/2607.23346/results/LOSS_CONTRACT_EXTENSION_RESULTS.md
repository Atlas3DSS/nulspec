# Post-hoc supervised-logit results

Status: **complete** (5/5 frozen seeds).

This outcome-motivated diagnostic changes only the terminal activation so supervised `CrossEntropyLoss` receives logits. It cannot alter the preregistered verdict.

| Model | n | Mean accuracy | SD | 95% t interval | Mean CE |
|---|---:|---:|---:|---:|---:|
| `control_student_logit_ce` | 5 | 95.152 | 0.385 | [94.674, 95.631] | 0.261 |
| `sprkd_logit_ce_random_init` | 5 | 94.792 | 0.193 | [94.553, 95.032] | 0.283 |

## Run-level outcomes

| Run | Logit Control-S | Logit SPRKD | Final SPRKD NHE count |
|---|---:|---:|---:|
| `loss-contract-seed-0` | 95.341 | 95.109 | 0 |
| `loss-contract-seed-1` | 95.094 | 94.819 | 0 |
| `loss-contract-seed-2` | 95.312 | 94.746 | 0 |
| `loss-contract-seed-3` | 95.501 | 94.615 | 0 |
| `loss-contract-seed-4` | 94.514 | 94.673 | 0 |
