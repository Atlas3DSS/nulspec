# Exploratory scratch-model Hessian traces

Status: **complete** (5/5 frozen seeds).

| Model | n | Mean trace | SD | 95% t interval |
|---|---:|---:|---:|---:|
| `control_student` | 5 | -1.767 | 15.277 | [-20.736, 17.201] |
| `rkd_paper_weak_teacher` | 5 | 66.924 | 110.546 | [-70.336, 204.184] |
| `rkd_upstream_asr_teacher` | 5 | -0.479 | 0.867 | [-1.555, 0.597] |
| `sprkd_paper_random_init` | 5 | -11.186 | 27.119 | [-44.860, 22.487] |
| `sprkd_upstream_direct_init` | 5 | -370.041 | 862.682 | [-1441.202, 701.120] |

These are 100-probe estimates on the fixed released 100-image batch. They test ordering only and are not estimates of the paper's under-specified Table 1 values.

## Run-level trace estimates

| Run | Exact SPRKD | Intent SPRKD | Control-S | Exact RKD | Intent RKD |
|---|---:|---:|---:|---:|---:|
| `hessian-seed-0` | -18.018 | -59.615 | -26.560 | 0.059 | 139.317 |
| `hessian-seed-1` | -1911.652 | 0.000 | 0.075 | -0.500 | 29.857 |
| `hessian-seed-2` | -2.906 | 0.000 | 0.000 | 0.302 | 72.707 |
| `hessian-seed-3` | 0.000 | 3.683 | 2.194 | -0.335 | 190.224 |
| `hessian-seed-4` | 82.370 | 0.000 | 15.455 | -1.923 | -97.485 |
