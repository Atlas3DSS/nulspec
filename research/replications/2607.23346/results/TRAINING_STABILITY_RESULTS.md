# Post-hoc training-stability results

Status: **complete** (5/5 frozen seeds).

This descriptive analysis was specified after seed 1 exposed a sharp epoch-level drop. It does not alter the preregistered verdict.

| Seed | Model | Best (epoch) | Final | Largest one-epoch drop (arrival) |
|---:|---|---:|---:|---:|
| 0 | `control_student` | 95.819 (428) | 95.573 | 1.049 (282) |
| 0 | `control_teacher` | 95.804 (472) | 95.428 | 4.211 (25) |
| 0 | `rkd_paper_weak_teacher` | 73.463 (252) | 71.769 | 3.465 (116) |
| 0 | `rkd_upstream_asr_teacher` | 50.059 (1) | 50.059 | 0.000 (2) |
| 0 | `sprkd_paper_random_init` | 95.819 (478) | 95.486 | 2.329 (30) |
| 0 | `sprkd_upstream_direct_init` | 95.935 (177) | 95.645 | 3.046 (10) |
| 1 | `control_student` | 95.818 (299) | 95.594 | 9.636 (3) |
| 1 | `control_teacher` | 95.501 (93) | 95.095 | 2.909 (11) |
| 1 | `rkd_paper_weak_teacher` | 74.084 (417) | 73.079 | 1.165 (258) |
| 1 | `rkd_upstream_asr_teacher` | 49.782 (1) | 49.782 | 0.000 (2) |
| 1 | `sprkd_paper_random_init` | 93.525 (14) | 49.782 | 43.417 (21) |
| 1 | `sprkd_upstream_direct_init` | 95.051 (309) | 94.473 | 42.875 (19) |
| 2 | `control_student` | 94.907 (84) | 50.499 | 44.264 (95) |
| 2 | `control_teacher` | 95.587 (150) | 95.139 | 6.149 (28) |
| 2 | `rkd_paper_weak_teacher` | 72.492 (83) | 71.559 | 1.759 (9) |
| 2 | `rkd_upstream_asr_teacher` | 50.499 (1) | 50.499 | 0.000 (2) |
| 2 | `sprkd_paper_random_init` | 92.606 (15) | 50.499 | 41.457 (18) |
| 2 | `sprkd_upstream_direct_init` | 94.459 (498) | 93.533 | 26.791 (17) |
| 3 | `control_student` | 95.789 (471) | 95.500 | 0.999 (75) |
| 3 | `control_teacher` | 95.688 (132) | 95.268 | 3.162 (12) |
| 3 | `rkd_paper_weak_teacher` | 69.665 (14) | 69.347 | 1.143 (488) |
| 3 | `rkd_upstream_asr_teacher` | 49.971 (1) | 49.971 | 0.000 (2) |
| 3 | `sprkd_paper_random_init` | 94.566 (436) | 94.436 | 44.024 (224) |
| 3 | `sprkd_upstream_direct_init` | 93.264 (22) | 49.971 | 42.172 (27) |
| 4 | `control_student` | 95.536 (402) | 94.943 | 0.890 (92) |
| 4 | `control_teacher` | 95.529 (345) | 95.283 | 1.100 (20) |
| 4 | `rkd_paper_weak_teacher` | 74.113 (165) | 71.777 | 5.028 (19) |
| 4 | `rkd_upstream_asr_teacher` | 49.652 (1) | 49.652 | 0.000 (2) |
| 4 | `sprkd_paper_random_init` | 94.227 (290) | 49.652 | 44.198 (144) |
| 4 | `sprkd_upstream_direct_init` | 95.428 (392) | 95.116 | 43.953 (29) |

Values are the released runner's unweighted validation-batch means. Final sample-weighted metrics remain the primary outcomes.
