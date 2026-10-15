# Profiling report: YoungZ365/SOD issue #19 (training time and step count)

## 0 What we did for you

**WHAT WE DID**
Ran the repository's own stepwise regularizer code (_apply_token_kl_regularizer and its helpers from verl/trainer/ppo/ray_trainer.py; Apache-2.0, commit 110c4b8e843aee274d3cd648199569369ee2403e) on one Tesla V100-PCIE-32GB for under one GPU-minute (44.7 s wall) with synthetic tensors; full training, data and weights were not run or downloaded.

**WHAT TO CHANGE**
- Set trainer.total_training_steps=120 (0.6B) or 150 (1.7B) in run_sod.sh, which sets one epoch at batch 64 and no stop step (about 469 steps): at the paper's 1,052.3 s/step, ~137.1 h → 35.1 h (0.6B). Calculated from the paper and issue figures, not measured here; no matched A800/H20 run was done.
- In _extract_step_boundaries, replace the per-token .item() scan (a host-GPU sync per mask position) with bulk boundary extraction and batched reductions: before measured at 7.81 s per call (1,024 trajectories x 128 tokens, with the per-sample log write), 3.62 s at batch 64 x 1,024 tokens; after NOT measured (untested suggestion).

**DELIVERABLES**
harness/profile_sod_regularizer.py (extracts and times the pinned repository functions on synthetic tensors), measurements/regularizer.json (timings, peak allocated memory, GPU/runtime, source hash); timing table, projection table and config-vs-paper gap table in this report.

## 0. Read this first

The public report is consistent on time per update: Table 4 gives **1,052.3 s/step** for SOD 0.6B, while the issue reporter says about **1,042 s/step** on 8×A800. That is a roughly 1% difference. The paper reports 120 updates for the 0.6B SOD run, while the released [run_sod.sh](https://github.com/YoungZ365/SOD/blob/110c4b8e843aee274d3cd648199569369ee2403e/examples/SOD/run_sod.sh) defaults to one pass over the roughly 30K RL set at batch size 64 (about 469 batches). The update-count difference is about 3.9× and explains most of the reported wall-time gap. The issue’s stated multiplication, 1,042 seconds × 470 steps, works out to about 136 hours rather than 150.

I profiled the pinned repository implementation of `_apply_token_kl_regularizer` on one V100 using synthetic tensors. At the configured 1,024 rollout count but only 128 tokens per trajectory, the median was 7.81 seconds per call. This includes the repository’s per-sample stepwise log writing. It is a targeted algorithm-path profile, not an end-to-end training result. Full SOD training was not run.

Nothing was posted, commented, emailed, or sent. This deliverable needs owner approval before anything goes out.

## 1. Pinned commit/licence/environment

- Repository: [YoungZ365/SOD](https://github.com/YoungZ365/SOD). GitHub API reports Apache-2.0; the API was checked before cloning.
- Pinned commit: [`110c4b8e843aee274d3cd648199569369ee2403e`](https://github.com/YoungZ365/SOD/commit/110c4b8e843aee274d3cd648199569369ee2403e), `v2-update`.
- Paper: [SOD, arXiv:2605.07725v3](https://arxiv.org/abs/2605.07725), including Table 4 and Appendix C.1.
- Issue: [YoungZ365/SOD #19](https://github.com/YoungZ365/SOD/issues/19). Its two existing comments were read; none was added.
- Host: our GPU host, an unprivileged account; Tesla V100-PCIE-32GB, UUID `GPU-725106e3-11df-e1fc-003e-99f071a4e353`; 32 GiB reported VRAM. The card was bound by UUID. Post-run `nvidia-smi` showed 4 MiB used, 34 °C and 0% utilization; no compute process remained.
- Runtime: Python 3.12.3 and PyTorch 2.5.1+cu124 in a venv under the disposable run directory. Timed command used `nice -n 10 taskset -c 24-31`. The measured profile took 44.70 seconds wall time in total, including process startup and all cases (under 1 GPU-minute).
- Data and weights: the README links Open-AgentRL SFT, RL and evaluation datasets plus Qwen3/SOD models. Hugging Face dataset API/cards exposed no license metadata; the evaluation README was unavailable. Model API metadata identifies Apache-2.0 for Qwen3-0.6B, SOD-0.6B and SOD-GRPO_teacher-4B, but no weights were downloaded. No dataset terms could be verified, so synthetic inputs were used.

## 2. What was run

The harness reads only `verl/trainer/ppo/ray_trainer.py` from the pinned checkout and extracts the repository implementations of `_extract_step_boundaries`, `compute_stepwise_opd_weights`, `_write_stepwise_log`, and `_apply_token_kl_regularizer`. It calls the exact function bodies with synthetic student/teacher log probabilities, assistant-token masks, and advantages. The repository source SHA-256 was recorded in `measurements/regularizer.json`.

The profile includes the code’s scalar token-mask scan, stepwise weight calculation, advantage update, and detailed log append. It does not load the full trainer module or run its setup/install scripts. No tokenizer, language model, optimizer, rollout, distributed worker, reward function, training data, or model weight participated.

The final harness measured two warm-ups and ten steps for small and moderate cases, one warm-up and three steps at batch 64, and one warm-up and two steps at batch 1,024. Synthetic assistant spans were used to form four, eight or sixteen turns. The batch-1,024 case uses only 128 tokens per trajectory, far below the configured 20,480-token maximum.

## 3. Where the time goes

| Synthetic profile case | Median seconds/call | CUDA peak allocated during case |
|---|---:|---:|
| Batch 2 × 128 tokens, 4 assistant spans | 0.0176 | 11.5 KiB |
| Batch 4 × 512 tokens, 8 assistant spans | 0.1249 | 88.5 KiB |
| Batch 64 × 1,024 tokens, 16 assistant spans | 3.615 | 2.75 MiB |
| Batch 1,024 × 128 tokens, 4 assistant spans | 7.809 | 5.50 MiB |

These memory figures are PyTorch allocated memory for the synthetic call, not total card memory or model-training memory. The paper reports a 87.6 GB peak-memory figure for the 0.6B SOD run on 8×H20; it does not establish a comparable peak for this V100 profile.

At the largest measured sample count, `_extract_step_boundaries` calls `.item()` on each response-mask position in a Python loop. Each scalar read synchronizes host and GPU work. The observed call time therefore grows with mask length and batch size, despite the paper describing the additional arithmetic as per-step averaging plus O(K) scalar operations. Our 1,024 × 128 case is 7.81 seconds; it is not a basis for extrapolating to full response lengths because actual length distributions, padding and tool-turn counts were not available. The routine also writes a detailed per-sample log each call.

## 4. Variants

All rows below are **measured** on the assigned V100 and run the same code path; only synthetic batch/sequence/turn dimensions changed.

| Variant | Median time/call | Repetitions | Notes |
|---|---:|---:|---|
| Small | 0.0176 s | 10 | Batch 2, 128 tokens |
| Moderate | 0.1249 s | 10 | Batch 4, 512 tokens |
| Batch 64 | 3.615 s | 3 | 1,024 tokens, 16 spans |
| Rollout count, short sequence | 7.809 s | 2 | Batch 1,024, 128 tokens, 4 spans |

No FP8, bf16, model-size, generation, optimizer, sequence-parallel, or multi-GPU variants were run. The released SOD script does not pass an FP8 quantization setting; the paper specifies asynchronous vLLM rollout with tensor parallelism 4 but does not document FP8 use. This does not establish which settings were used in the authors’ private H20 runs.

## 5. Projection

These are calculations from public/reported step times, **not measurements by this run**.

| Basis | Steps | Seconds/step | Projected elapsed time | Status |
|---|---:|---:|---:|---|
| Paper Table 4, SOD 0.6B | 120 | 1,052.3 | 35.08 h (reported as 35.1 h) | Paper report; multiplication checked |
| Released script, one pass over approximately 30K at batch 64 | ~469 | 1,052.3 | ~137.1 h | Estimate at paper’s time/step |
| Issue reporter’s displayed step time and approximate step count | ~470 | 1,042 | ~136.0 h | Estimate from issue values; inconsistent with the issue’s “~150 h” total |
| Paper Table 4, SOD 1.7B | 150 | 1,105.4 | 46.06 h (reported as 46.1 h) | Paper report; multiplication checked |

The 1,042 s/step reported by the A800 user is close to the 1,052.3 s/step H20 value. On the figures supplied, multiplying the public script’s roughly 3.9× larger step count explains most of the 4× wall-time gap. This does not rule out hardware or rollout differences; no matched A800/H20 experiment was conducted.

## 6. Config-vs-paper gap table

| Item | Paper / issue evidence | Pinned release source | Finding |
|---|---|---|---|
| 0.6B SOD duration | Table 4 reports 120 updates, 1,052.3 s/update, 35.1 h on 8×H20 | `run_sod.sh` sets `trainer.total_epochs=1` | A full script-default pass is not the 120-step reported run |
| 1.7B SOD duration | Table 4 reports 150 updates, 1,105.4 s/update, 46.1 h | Same one-epoch default | Release script does not encode the reported update limit |
| RL batch / dataset | Paper says batch 64, at most one epoch; issue describes roughly 30K samples | `train_batch_size=64`; dataset path points to Open-AgentRL-30K | About 469 batches if the dataset has exactly 30,000 rows and no filtering |
| Stop behavior | Paper gives step totals but no early-stop criterion in the cited implementation details | `total_training_steps` defaults to `len(train_dataloader) * total_epochs`; an explicit override is supported. The loop stops at this count. | No convergence-based early stop is visible in the inspected loop. `run_sod.sh` does not set the override. Exact paper command or manual-stop criterion is missing from the release script. |
| Author’s issue reply | Reply says reported cost reflects steps needed to reach convergence, while referring to the 4B→1.7B experiment | Current arXiv v3 assigns 120 SOD steps to 0.6B and 150 to 1.7B | Reply’s scale label does not match the current paper’s table. Clarify exact checkpoint/model and stop rule before claiming a full reproduction. |
| Rollout settings | Paper says asynchronous vLLM, tensor parallel 4, max 16 tool-call turns | Script sets `infer_tp=4`, `max_turns=16`, `rollout.mode=async`, `n=16`, max response 20,480 | Broadly aligned in the visible script |
| FP8 | Issue asks whether H20 FP8 was used; paper does not specify it | Script contains no FP8 quantization flag; rollout default dtype is bfloat16 | Public artifacts do not answer what the authors enabled on H20 |
| Peak memory | Table 4 reports 87.6 GB for 0.6B SOD | No single-GPU profile of full student/teacher training performed | The 32 GiB V100 is not representative of the published 8×H20 setup |

The issue’s `1,042 × 470` estimate is 489,740 seconds or 136.0 hours. A 150-hour total would need about 1,149 seconds/update at 470 steps, or about 518 steps at 1,042 seconds/update.

## 7. Suggestions

- **Source-confirmed next step:** rerun the public script with `trainer.total_training_steps=120` for the 0.6B Table 4 row and `=150` for the 1.7B row, if those are indeed the intended experiments. Save the exact command and selected checkpoint. Ask the authors to document any convergence or manual-stop rule before treating that command as an exact reproduction.
- **Estimated / untested optimization:** replace the Python loop’s per-token `.item()` boundary scan with bulk boundary extraction and batched reductions. The measured batch-1,024 short-sequence case is 7.81 seconds per call; expected benefit depends on real response lengths and whether the detailed log output remains enabled.
- **Source-confirmed reproducibility detail:** publish the exact Open-AgentRL dataset revision/row count, student and teacher checkpoints, vLLM version, quantization/dtype flags, and per-stage timings. This would distinguish hardware effects from update count, response lengths, tool retries, and evaluation/checkpoint overhead.
- **Estimated / untested hardware check:** compare one fixed step on 8×A800 and 8×H20 using the same checkpoint, batch, prompts, vLLM settings and stop count. The reported 1,042 vs 1,052.3 seconds per step already suggests that the major discrepancy is update count, but it is not a controlled comparison.

## 8. Ephemeral-run statement

Your code, weights and data were handled only in a throwaway, unprivileged account on a GPU host with no access to our other files. Everything we fetched or built was deleted when the run ended; only numbers and the small harness we wrote were kept. Nothing was posted or sent, and no one was contacted before this report.

## 9. What we could not run or verify

- Full SOD training, including its 8-GPU Ray/vLLM setup, 4B teacher, 0.6B student, rollout, optimizer and convergence. The assigned single 32 GiB V100 is not the paper’s eight H20s and cannot reproduce the full setup.
- Real SFT/RL/evaluation datasets or checkpoint weights. Dataset cards/API did not expose license terms; none was downloaded.
- The full response-length distribution, average number of tool turns, exact per-stage H20 timing, or exact run commands used for Table 4.
- Whether FP8 quantization was active in the authors’ H20 rollout, or how FP8 changes A800 vs H20 performance.
- A controlled comparison of hardware speed, energy, or end-to-end peak memory. No V100 full-training memory number is claimed.

## 10. Files

- `SUMMARY.md`
- `REPORT.md`
- `harness/profile_sod_regularizer.py` — extracts and profiles the pinned repository’s stepwise regularizer with synthetic tensors.
- `measurements/regularizer.json` — timings, peak allocated tensor memory, GPU/runtime and source hash.

Accelerate everything.
