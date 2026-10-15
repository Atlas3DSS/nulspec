# Profiling report: SC²-WM training cost (GitHub issue sunrise-yuze/SC2_WM #6)

Prepared 2026-10-14. Nothing in this report has been sent to, posted to, or discussed with the repository authors.

## 0 What we did for you

**WHAT WE DID**
Ran your released training code (MIT, commit f2f2f5ff2e1f21a08f7d7c51fbbd5c17b0d6778b, released weights, main.bash arguments) unmodified on one Tesla V100-PCIE-32GB for about 35 GPU-minutes (12 timed episodes per run), with the Habitat simulator replaced by synthetic frames because Matterport3D terms were not accepted.

**WHAT TO CHANGE**
- In label_pooling (ground projection), replace the per-cell Python loop with one unique + index_put_(accumulate=True) histogram: segmentation stage 309.9 s → 6.4 s over 12 episodes, whole episode 46.2 s → 20.6 s (2.24x), output max abs difference 6e-8.
- In run_nerf_feature, do one device-to-host copy of the ray densities for all 64 rays and build sample indices on the CPU instead of per-ray .cpu() and re-upload: 20.6 s → 16.4 s per episode (a further 1.25x, 2.81x combined; 22,000 episodes 282 h → 100 h, simulator excluded), outputs bit-identical with a fixed seed.
- Build torch_kdtree with 70-real prepended to its CUDA arch list (default list starts at sm_75): V100 fails with "no kernel image is available" → runs (all V100 numbers above); also place bert-base-uncased config.json at vlnce_baselines/bert-base-uncased, the path the code reads (README says bert_config/), or model construction fails.

**DELIVERABLES**
harness/bench.py (benchmark driver; contains both patch bodies label_pooling_vec and the batched ray selection, with equivalence checks), harness/fakeenv.py (synthetic stand-in for the simulator), harness/stubs.py (habitat import stubs), harness/run1.sh (launch script); measurements/timing_baseline.json, timing_patch1.json, timing_patch1+2.json (per-episode and per-stage timings); measurements/gpu_trace_baseline.csv, gpu_trace_patch1.csv, gpu_trace_patch1+2.csv (2 Hz GPU traces); timing table, config-gap table (section 6) and suggestion table (section 7) in this report.

## 0. Read this first

1. **"SC2" here is not StarCraft II.** SC²-WM is "Self-Correcting World Model" for Vision-and-Language Navigation in Continuous Environments (VLN-CE). The training loop drives Habitat-Sim on Matterport3D scenes. No Blizzard binary or licence is involved.
2. **What was and was not measured.** Everything in the training iteration that runs in the authors' Python code (feature generation, segmentation and ground projection, NeRF-style feature synthesis, the navigation model, backward pass, optimiser) was measured, executing the released code unchanged, on a Tesla V100. The **simulator** (Habitat-Sim rendering and agent movement) was **not** run, because Matterport3D scenes require the requester to accept the Matterport Terms of Use, which we did not do. The simulator was replaced by a synthetic stand-in that returns random RGB and analytically generated room depth at zero cost. Every number below is therefore "everything except the simulator". The simulator share of the reported 60 s/episode cannot be separated from this data.
3. **Headline.** On the released code, the non-simulator part of one training episode (one optimiser iteration; batch size 1) costs 46.2 s on our V100 host (mean of 12 episodes, 14.9 agent steps each). 56% of that is one Python loop in the ground-projection code and 30% is a per-ray Python loop in the NeRF-style feature synthesis. Two small patches that leave outputs numerically identical cut it to 16.4 s (2.81x). The GPU is about 9% busy on the released code (18% after patches): the workload is CPU and Python bound, not GPU bound.
4. **The 40-hour claim.** 40 h over 22,000 episodes is 6.5 s/episode. The issue reports 60 s/episode on a 4090, which is 9.2x slower. Our measured non-simulator cost alone, on a slow contended host, is 46 s (released) or 16 s (patched). We cannot say whether the paper's number used an optimised internal version; that is the authors' question to answer, and this data neither confirms nor refutes it.

## 1. Pinned commit and exact environment

| Item | Value |
|---|---|
| Repo | https://github.com/sunrise-yuze/SC2_WM, shallow clone, commit `f2f2f5ff2e1f21a08f7d7c51fbbd5c17b0d6778b` (2026-09-16 00:18 -0700, "docs: surface HuggingFace/ModelScope links at top and restyle header") |
| Licence | MIT (LICENSE: "Copyright (c) 2026 SC²-WM Authors"); GitHub API licence key `mit`. Profiling a public MIT-licensed repo is permitted. |
| Weights | The authors' public Hugging Face repo `zhuyuze/SC2_WM` (not gated; no licence tag in the hub metadata, README says the repo is MIT). Used: `data/checkpoints/ckpt.46600.pth`, `pretrained/{model_step_100000.pt, cwp_predictor.pth, NeRF_p16_8x8.pth, segm.pt, resnet18-f37072fd.pth}`, `data/ViT-B-16.pt`. Used for timing only, deleted afterwards. |
| Host | our GPU host, an unprivileged account; Intel Xeon Gold 6152 @ 2.1 GHz (88 threads), **host load average 67-74 of 88 during runs** (another job); our process ran `nice -n 10`, pinned to 8 CPUs (`taskset -c 0-7`), `OMP_NUM_THREADS=4`, `CUDA_VISIBLE_DEVICES=0` |
| GPU | 1x Tesla V100-PCIE-32GB (sm_70), driver 580.178.04. Peak memory use 4.7 GB allocated / 5.0 GB reserved; nvidia-smi shows 4.6-5.2 GB. |
| CPU speed reference | A pure-Python `for i in range(20_000_000): s += i` loop takes 4.34 s on this host under load. This is slow; see section 5 for how it affects scaling. |
| Python / torch | Python 3.12.3 (system); torch 2.5.1+cu124, torchvision 0.20.1+cu124; `torch.cuda.get_arch_list()` = `sm_50 sm_60 sm_70 sm_75 sm_80 sm_86 sm_90` (sm_70 present) |
| Other packages | numpy 1.26.4, scipy 1.17.1, transformers 4.44.2, open3d 0.20.0, gym 0.23.1, yacs 0.1.8, numpy-quaternion 2024.0.13, opencv-python-headless 4.11.0.86 |
| Native extensions | tiny-cuda-nn @ `3daa6e5b8b8e0fa17971a1a20acfbb3754494b38` (built TCNN_CUDA_ARCHITECTURES=70); torch_kdtree @ `5b6752985e5d8f21deb131bc394cde1f3baeabc3`, built with nvcc 12.9.86 |
| GPU monitoring | `nvidia-smi --query-gpu=utilization.gpu,utilization.memory,memory.used,power.draw,clocks.sm -lms 500` (a query loop at 2 Hz instead of the `dmon` subcommand; same counters) |

**Deviations from the repo's stated environment** (README pins Python 3.7, torch 1.12.1+cu113, habitat-sim 0.2.1, conda):

- torch 2.5.1+cu124 on Python 3.12 instead of torch 1.12.1 on Python 3.7. torch 1.12.1+cu113 has no wheel for Python 3.12, and 2.5.1 is the nearest release whose wheels still ship sm_70 kernels. Some numerical and dispatch differences from 1.12.1 are possible.
- habitat, habitat_baselines and habitat_sim are not installed. They are replaced by small stubs (`harness/stubs.py`) so the repo's own model and trainer modules import. The simulator is replaced by `harness/fakeenv.py`.
- The repo's `torch_kdtree` extension default CUDA arch list starts at sm_75, so it fails on a V100 with "no kernel image is available". We rebuilt it with `70-real` prepended. This is a V100-only issue.
- `vlnce_baselines/models/etp/vlnbert_init.py` reads `vlnce_baselines/bert-base-uncased`, while the README and layout document `bert_config/bert-base-uncased`. We placed bert-base-uncased `config.json` at the path the code reads. This is a repository defect independent of this study: following the README alone, training fails at model construction.

## 2. What was run

The harness (`harness/bench.py`) builds the authors' real `RLTrainer` (`vlnce_baselines/ss_trainer_ETP.py`), calls its own `_initialize_policy` with `main.bash` training arguments (`NUM_ENVIRONMENTS 1`, `IL.lr 1e-5`, `IL.load_from_ckpt True`, `IL.ckpt_to_load ckpt.46600.pth`, `IL.waypoint_aug True`, `MODEL.pretrained_path pretrained/model_step_100000.pt`, `IL.sample_ratio 0.75`, `IL.decay_interval 5000`), then calls its own `_train_interval(1, ...)`, which runs one full training episode: rollout, loss, `backward()`, grad clipping, AdamW step, and the per-iteration grad-norm/update-ratio bookkeeping. Nothing in the trainer was modified for the **baseline** runs. Timing wrappers (with `torch.cuda.synchronize()` before and after) were attached around `policy.net(mode=...)`, `run_img_segm`, the three U-Nets, `backward`, `optimizer.step`, and the CPU graph-building helpers.

Synthetic observations: per agent step the stand-in returns 24 sensors (RGB 224x224x3 uint8 random noise, depth 256x256x1 analytic z-depth of an empty 6x7x2.6 m box room seen from random poses, 12 camera orientations), a position/heading that moves to the chosen ghost node, and a fake geodesic distance that decreases by 0.5 m per step (teacher STOP at <1.5 m; the model also samples STOP). Episode length was therefore generated by the stand-in, not by real R2R episodes (observed 4 to 28 steps, mean 14.9). This is an assumption that affects every per-episode figure below; per-step figures are less sensitive.

Runs (all on GPU 0, one warm-up episode excluded, 12 timed episodes, identical RNG seed so the three runs executed the identical 179 agent steps):

| Run | Description | Total (12 ep) | s/episode | s/step |
|---|---|---|---|---|
| A. baseline | released code, unmodified | 554.1 s | 46.17 | 3.096 |
| B. + patch 1 | vectorised `label_pooling` (monkey-patch in harness) | 247.6 s | 20.63 | 1.383 |
| C. + patch 1 and 2 | also batched ray-selection loop in NeRF feature code | 197.3 s | 16.44 | 1.102 |

Total GPU-attached time for the engagement (all runs, including bring-up, equivalence checks and two aborted profiler runs) was approximately 35 minutes, from run logs; wall time about 1 h 30 min (22:30 to 00:00 PDT).

Per-episode time against agent steps (baseline) fits `ep_s = 2.49 * steps + 9.1` (R² 0.94, n=12): about 9 s of fixed per-episode cost plus about 2.5 s per additional step.

## 3. Where the time goes (non-simulator part)

Seconds are summed over 12 episodes and 179 agent steps.

| Stage | Baseline s (%) | s/step | After patches 1+2, s (%) | s/step |
|---|---|---|---|---|
| **Environment step (Habitat-Sim)** | **not measured** (stand-in: 0.07 s total) | - | not measured | - |
| Segmentation net + ground projection (`run_img_segm`; per-cell Python loop in `label_pooling`) | 309.9 (55.9%) | 1.731 | 6.3 (3.2%) | 0.035 |
| Feature generation, waypoint mode (`net.waypoint`: CLIP ViT-B/16 on the forward view, 12x NeRF-style feature synthesis with kd-tree queries and a per-ray Python loop, memory bank query/update, and in training 11 extra CLIP passes when `IL.waypoint_aug True`) | 164.5 (29.7%) | 0.919 | 113.8 (57.7%) | 0.636 |
| Feature generation, feature-field mode (`net.feature_field`: CLIP on 12 views at step 1 and 1 view later, point-cloud update) | 7.6 (1.4%) | 0.042 | 7.4 (3.7%) | 0.041 |
| 3 map U-Nets (occupancy, semantic, waypoint) | 5.5 (1.0%) | 0.031 | 5.2 (2.7%) | 0.029 |
| Occupancy from depth (`est_occ_from_depth`) | 1.4 (0.2%) | 0.008 | 1.2 (0.6%) | 0.007 |
| Model forward: navigation + panorama + language | 5.1 (0.9%) | 0.029 | 4.9 (2.5%) | 0.027 |
| Backward (once per episode, graph spans all steps) | 13.2 (2.4%) | 0.074 | 13.9 (7.1%) | 0.078 |
| Optimiser step + scaler | 0.2 (<0.1%) | 0.001 | 0.2 (0.1%) | 0.001 |
| CPU graph/feature assembly (`_nav_gmap_variable` etc.) | 4.4 (0.8%) | 0.025 | 4.1 (2.1%) | 0.023 |
| Everything else (rollout Python, 12-direction waypoint loops with per-element `.item()` syncs, per-iteration grad-norm/update-ratio bookkeeping, printing, GPU syncs) | 42.4 (7.7%) | 0.237 | 40.1 (20.4%) | 0.224 |
| Data loading | none: there is no DataLoader; observations come from the simulator | - | - | - |

Model forward/backward on the navigation network is about 3% of the time on the released code. The cost is dominated by (a) Python-level per-cell and per-ray loops that make thousands of tiny GPU launches and device-to-host copies per step, and (b) the number of sequential feature-synthesis calls per step. The cProfile of the patched configuration (2 episodes, noisy because of host load) shows the remaining top CPU consumers as host-to-device `.to()` copies, `linear` calls inside the NeRF/CLIP stack, `torch_kdtree` queries, `heapq.nlargest` and `scipy.signal.find_peaks` (still called per ray, but now on one bulk copy), and about 157,000 `parameters()` calls from `torch.nn.DataParallel` wrapping.

## 4. GPU utilisation and memory over time

From the 2 Hz nvidia-smi trace (`measurements/gpu_trace_*.csv`, 1,099 samples for the baseline run):

| Window of baseline run | GPU util mean / max | Memory used (MiB) | Power (W) |
|---|---|---|---|
| 0-60 s | 9.0% / 31% | 4,615 | 42.5 |
| 60-120 s | 8.7% / 26% | 4,646 | 43.2 |
| 120-180 s | 9.2% / 36% | 4,665 | 42.8 |
| 180-240 s | 8.1% / 25% | 4,715 | 42.2 |
| 240-300 s | 11.1% / 31% | 4,775 | 43.3 |
| 300-360 s | 8.9% / 28% | 5,152 | 42.1 |
| 360-420 s | 9.5% / 26% | 5,152 | 43.1 |
| 420-480 s | 8.5% / 29% | 5,152 | 42.3 |
| 480-540 s | 8.9% / 29% | 5,152 | 42.2 |
| 540-600 s | 8.4% / 21% | 5,153 | 43.2 |

Whole-run summary: baseline mean util 9.1% (65% of samples at or below 10%, none at or above 50%, max 36%), memory 4.9 GB mean (5.15 GB max), power 42.6 W mean (idle for this card is about 40 W), SM clock constant at 1,230 MHz (no thermal or power throttling). After patch 1 mean util 15.4%; after patches 1+2, 18.1%. The GPU is idle most of the time while Python and the CPU work. `nvidia-smi` utilisation means "a kernel was running during the sample period", not occupancy, so true SM utilisation is lower still.

## 5. Projection of the 22,000-episode schedule

Method: per-episode time from the 12-episode runs (non-simulator part, V100 host as described) multiplied by episode count. Paper schedule: 12,000 + 10,000 = 22,000 episodes.

| Configuration | s/episode | 22,000 episodes | 13,400 episodes (what `main.bash` runs from `ckpt.46600`) |
|---|---|---|---|
| Released code, V100 (measured) | 46.2 | **282 h (11.8 days)** | 172 h |
| + patch 1 (measured) | 20.6 | 126 h (5.3 days) | 77 h |
| + patches 1 and 2 (measured) | 16.4 | **100 h (4.2 days)** | 61 h |

All of these exclude the simulator, validation and checkpointing. The real figure is higher by the simulator time, which we could not measure.

**Scaled estimate for RTX 3090 and RTX 4090 (estimate, not measured; no such GPU was available).** The workload is mostly CPU and launch bound, so GPU spec ratios would be the wrong scaling rule. Assumption used:

- Split each episode into GPU-busy time (upper bound: mean nvidia-smi util x episode time, i.e. 9.1%, 15.4%, 18.1% for A, B, C) and the rest (CPU).
- GPU part speeds up by between the memory-bandwidth ratio (3090: 936/900 = 1.04x; 4090: 1008/900 = 1.12x) and the FP32 TFLOPS ratio (3090: 35.6/15.7 = 2.3x; 4090: 82.6/15.7 = 5.3x) relative to the V100.
- CPU part speeds up by 1.0x (pessimistic: same slow, contended host) to 3.0x (optimistic: a modern desktop CPU at about 5 GHz without a co-tenant job; an assumption, not measured; the authors' and the issue reporter's CPUs are unknown).

| Configuration | 3090, 22,000 episodes | 4090, 22,000 episodes |
|---|---|---|
| Released code | 97-281 h (15.8-46.0 s/episode) | 90-279 h (14.8-45.7 s) |
| + patch 1 | 44-125 h | 39-124 h |
| + patches 1 and 2 | 35-100 h | 31-99 h |

Cross-check against the issue: the reporter measured 60 s/episode on a 4090, including the simulator. Our released-code non-simulator range for a 4090 is 15-46 s/episode, so the simulator would account for roughly 14-45 s of their 60 s, which is plausible but not verifiable from this data. To reach "less than 40 hours" (6.5 s/episode) the whole pipeline including the simulator has to be about 9x faster than the reporter's. Patches 1+2 at the optimistic end of our range reach about 5 s/episode before simulator time.

## 6. Config-vs-paper gap table

Paper values are from the arXiv PDF (2608.07548) Appendix C and Section 4 text, extracted by a crude text extraction. "Not found" means not located in the extracted text, not that the paper omits it.

| Item | Paper | Released code and `main.bash` (commit above) | Gap or note |
|---|---|---|---|
| Hardware and time | single RTX 3090, "less than 40 hours" | simulator and model share GPU 0; `NUM_ENVIRONMENTS 1`, `IL.batch_size 1` | Issue's 60 s/episode vs implied 6.5 s/episode |
| R2R-CE schedule | init from weights pretrained for 25,000 iterations; stage 1: 12,000 episodes; stage 2: 10,000 episodes (22,000 total) | `main.bash`: `IL.iters 60000` resuming `ckpt.46600.pth` (stored iteration 46600), so 13,400 more iterations; `iter_train.yaml` default `IL.iters 30000`. One iteration is one episode. | 46,600 is close to 25,000 + 22,000 = 47,000 (our inference, not stated by the authors), so the released checkpoint appears to be the end of the paper schedule. The shipped `main.bash` does not reproduce a 12,000+10,000 run from scratch. |
| Learning rate | stage 1 1e-5 (all modules); stage 2 4e-6 with language encoder frozen | single `IL.lr 1e-5` for all four optimiser groups; no scheduler; no 4e-6 anywhere in `ss_trainer_ETP.py` | The two-stage schedule is not implemented as a config option |
| Which modules train | stage 1 trains all modules jointly | `_setup_trainable_params('train')` freezes `vln_bert.embeddings` and `vln_bert.lang_encoder` (about 87.6 M parameters) from iteration 0; code comment: "comment out this line when finetuning to defreeze" | Stage 1 as described cannot be run without editing code |
| Initial backbone checkpoint | pretrained 25,000 iterations | `iter_train.yaml` default `pretrained_path` is `model_step_82500.pt`; `main.bash` passes `model_step_100000.pt` | Which one matches "25,000 iterations" is unclear |
| Teacher/sample ratio | not found | `sample_ratio = 0.75 ** ((idx - 15000) // decay_interval + 1)`; yaml `decay_interval 3000`, `main.bash` 5000. At idx 46,600 with 5,000 this is 0.75^7 = 0.13 | A schedule in the code but not in the extracted paper text |
| `IL.waypoint_aug` | not found | yaml default `False`; `main.bash` sets `True` | With `True`, training runs 11 extra CLIP forward passes per step (`rgb_30` ... `rgb_330`) and needs all 24 sensors from the simulator |
| Simulator sensors | not found | `_set_config` appends 11 extra RGB and 11 extra depth cameras to the base pair (24 sensors) | `get_observation_at` is called twice per training step and returns all sensors (static reading; render cost not measured) |
| TTA threshold | tau = 0.5 percentile | `IL.tta_thres 0.5` | Matches |
| TTA learning rate | not found | `IL.tta_lr 6e-7`, `tta_decay 0.0` | Not checked against the paper |
| Optimiser | not found | `torch.optim.AdamW` (default weight decay 0.01), AMP via `autocast` and `GradScaler`, grad-clip 70 | AMP is already on |
| Max steps per episode | "predefined maximum" | `IL.max_traj_len 30` | - |
| Back-to-node algorithm | not found | yaml `back_algo teleport` (train); eval flags use `control` | - |
| Optimiser state on resume | n/a | `IL.is_requeue True`: in our environment the load printed "Optim_state is not loaded" (a bare `except` swallows the reason) | Possibly environment dependent (torch 2.5.1 vs 1.12.1); Adam moments would restart empty |
| Setup path | n/a | `vlnce_baselines/bert-base-uncased` vs documented `bert_config/bert-base-uncased` | Defect (section 1) |
| V100 support | n/a | `torch_kdtree` default arch list excludes sm_70 | Fixable by a build flag |

## 7. Suggestions for closing the gap

Status key: **measured** = implemented in the harness and timed on identical work with a numerical-equivalence check; **estimated** = not implemented, estimated from the profile; **sim** = needs the simulator, unmeasured.

| # | Change | Status | Effect |
|---|---|---|---|
| 1 | In `label_pooling` (ground projection of segmentation labels), replace the Python loop over every occupied map cell (about 1,700-2,300 cells per call, several tiny GPU ops and a sync per cell, called twice per step) with one `unique` + `index_put_(accumulate=True)` histogram. | **measured** | Segmentation stage 309.9 s to 6.4 s (48x). Whole iteration 554.1 s to 247.6 s (**2.24x**). Output max absolute difference 6e-8 (float rounding) on 3 calls. |
| 2 | In the NeRF-style feature synthesis (`run_nerf_feature`), do one device-to-host copy of the ray densities for all 64 rays and build the sample indices on the CPU, instead of per-ray `.cpu()`, a tensor build and a device copy (64 rays x 12 views x steps). Same `find_peaks`/`nlargest` logic kept. | **measured** | 247.6 s to 197.3 s (further **1.25x**; combined **2.81x**). With the RNG seeded identically, outputs were bit-identical (max diff 0.0 on 6 calls; the layer has dropout, so the check needs a fixed seed). |
| 3 | Make the 12 direction queries in waypoint mode one batched call (kd-tree queries, neighbour gather, `fcd_aggregation`, `clip_mlp`, transformer for all 12 views together), keep the scene features on the GPU instead of a NumPy gather and re-upload each call, and update the kd-tree incrementally instead of rebuilding each step. | estimated | `net.waypoint` is 58% of the patched iteration (0.64 s/step). If this part drops 2-4x, the whole iteration drops 1.4-1.8x on top of #1 and #2. |
| 4 | Run several episodes concurrently (parallel envs in one process, or N worker processes sharing the GPU). The GPU is 9-18% busy, so it has room; the limit is CPU cores. | estimated; changes the optimisation (batch 1 to N) | Up to roughly N-fold throughput for N up to 4-8 if cores are available; needs a convergence check because the effective batch size changes. |
| 5 | Remove the single-device `torch.nn.DataParallel` wrapper around `policy.net` (its `forward` iterates all parameters and buffers every call; about 157,000 `parameters()` calls over 2 profiled episodes). | estimated | Roughly 3-5% of CPU time. |
| 6 | Remove per-iteration debug bookkeeping (module grad norms with `.item()`, parameter clones and update-ratio loop, prints) or run it every N iterations. | estimated | Part of the "everything else" bucket (20% of the patched iteration includes all remaining Python); likely low single digits. |
| 7 | Simulator side: do not request 24 sensors every observation (the 11 extra RGB-D pairs are only needed at step 1 and for the `waypoint_aug` reconstruction loss), avoid the duplicate full-sensor render per step, and review `get_cand_real_pos`, which the code documents as executing actions in the simulator for each candidate during training. | sim, unmeasured | Cannot be quantified without Matterport3D. Potentially the largest remaining item. |
| 8 | Mixed precision / CUDA graphs on the CLIP and navigation networks. | not recommended yet | AMP is already used in the trainer. With the GPU 9-18% busy, faster kernels barely change wall time until the CPU-side items above are fixed. |

Expected combined effect of 1+2 (measured) plus 3 (estimated): about 4-5x on the non-simulator iteration on this host (46 s to about 10-12 s), before any simulator-side change and before any faster CPU. This is not a prediction of the authors' internal numbers.

## 8. Ephemeral-run statement

Your code, weights and data were handled only in a throwaway, unprivileged account on a GPU host with no access to our other files. Everything we fetched or built was deleted when the run ended; only numbers and the small harness we wrote were kept. Nothing was posted or sent, and no one was contacted before this report.

## 9. What we could not run or verify

- The Habitat-Sim environment and Matterport3D scenes (Terms of Use not accepted by us). The simulator share of the time, real episode lengths, real depth statistics, and `get_cand_real_pos` cost are unmeasured. The label-pooling cost depends on the number of occupied cells per frame; synthetic room depth gave 1,700-2,300 cells per call, and real scenes could differ, which would change the baseline segmentation cost and the size of patch 1's gain (but not the loop structure).
- Real R2R-CE training episodes, convergence, accuracy, and whether the patches change training dynamics (the patched functions were numerically equivalent on test calls, which is not a proof for all inputs).
- The authors' pinned environment (Python 3.7, torch 1.12.1+cu113, habitat-sim 0.2.1). We used torch 2.5.1 on Python 3.12.
- RTX 3090 or RTX 4090 hardware: the 3090/4090 figures are scaled estimates (section 5) with a wide range because the CPU speed of the reporter's and authors' machines is unknown.
- The host was shared (load average about 70 of 88) and our process ran at reduced priority on 8 CPUs. Absolute seconds would differ on an idle machine, probably lower for this CPU-bound workload. The V100 numbers are best used as ratios (baseline vs patched) rather than absolute speed.
- `torch.profiler` was attempted and abandoned (the run took 69 s for a 12-step episode and was terminated before the table was written). The breakdown comes from synchronised wrapper timers plus cProfile for the CPU call structure. cProfile figures are noisy and are used qualitatively only.
- GPU-busy time is bounded by nvidia-smi utilisation, a coarse upper bound; kernel-level GPU time was not measured.
- Whether the paper's "less than 40 hours" used a different code path, a different (cached or pre-rendered) feature pipeline, or fewer simulator sensors. The paper text we extracted does not say.
- RxR-CE training, evaluation with test-time adaptation, multi-GPU DDP paths, and the legacy `dagger_trainer.py` were not exercised.
- The paper PDF was text-extracted crudely; the gap table's paper column should be checked against the PDF before anyone relies on it.
- Optimiser-state restoration failed in our environment (section 6); we did not determine the cause.

## 10. Files in this folder

- `REPORT.md` this report; `SUMMARY.md` owner summary.
- `measurements/timing_{baseline,patch1,patch1+2}.json` per-episode and per-stage timing; `measurements/gpu_trace_*.csv` 2 Hz nvidia-smi traces.
- `harness/` stubs, synthetic environment, benchmark driver and launch script used to produce the numbers (no repository code).

Accelerate everything.
