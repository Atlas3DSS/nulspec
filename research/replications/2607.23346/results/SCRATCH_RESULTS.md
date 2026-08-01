# Scratch-run results

Status: **complete** (5/5 frozen seeds).

| Model | n | Paper acc. | Mean acc. | SD | 95% t interval | Mean CE |
|---|---:|---:|---:|---:|---:|---:|
| `asr_mutated_teacher` | 5 | — | 49.997 | 0.322 | [49.598, 50.396] | 0.747 |
| `control_student` | 5 | 94.470 | 86.421 | 20.078 | [61.491, 111.351] | 0.449 |
| `control_teacher` | 5 | 94.500 | 95.237 | 0.130 | [95.075, 95.398] | 0.360 |
| `rkd_paper_weak_teacher` | 5 | 70.100 | 71.507 | 1.361 | [69.817, 73.196] | 0.592 |
| `rkd_upstream_asr_teacher` | 5 | 70.100 | 49.997 | 0.322 | [49.598, 50.396] | 0.747 |
| `sprkd_paper_random_init` | 5 | 94.800 | 67.977 | 24.634 | [37.390, 98.564] | 0.633 |
| `sprkd_upstream_direct_init` | 5 | 94.800 | 85.742 | 20.012 | [60.893, 110.590] | 0.455 |
| `weak_teacher_0` | 5 | — | 71.367 | 1.499 | [69.506, 73.229] | 0.584 |
| `weak_teacher_1` | 5 | — | 68.528 | 11.045 | [54.814, 82.243] | 0.600 |
| `weak_teacher_2` | 5 | — | 67.123 | 9.953 | [54.765, 79.482] | 0.604 |
| `weak_teacher_ensemble_mean` | 5 | 70.130 | 69.006 | 4.177 | [63.820, 74.193] | 0.596 |

Accuracies and losses are final, sample-weighted full-validation metrics. Intervals describe fresh-training variability over the frozen seeds; they are not prompt/bootstrap intervals.

## Run-level outcomes

| Run | GPU | Exact SPRKD | Intent SPRKD | Control-S | Exact RKD | Intent RKD |
|---|---|---:|---:|---:|---:|---:|
| `seed-0` | NVIDIA GeForce RTX 4090 | 95.631 | 95.472 | 95.559 | 50.044 | 71.785 |
| `seed-1` | NVIDIA RTX PRO 6000 Blackwell Workstation Edition | 94.470 | 49.797 | 95.588 | 49.797 | 73.077 |
| `seed-2` | NVIDIA GeForce RTX 3090 | 93.512 | 50.508 | 50.508 | 50.508 | 71.582 |
| `seed-3` | NVIDIA RTX PRO 6000 Blackwell Workstation Edition | 49.971 | 94.441 | 95.501 | 49.971 | 69.318 |
| `seed-4` | NVIDIA GeForce RTX 3090 | 95.123 | 49.666 | 94.949 | 49.666 | 71.771 |
