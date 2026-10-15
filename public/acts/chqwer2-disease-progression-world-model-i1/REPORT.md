# Profiling report: Step-1 autoencoder training cost (GitHub issue chqwer2/Disease-Progression-World-Model #1)

## 0 What we did for you

**WHAT WE DID**
Ran your released Step-1 autoencoder training script (Apache-2.0, commit ac2ca4d8abb6f3434045260ff1a6b5f37459b5bb, script step1_v2_axes.py) unmodified on one Tesla V100 32 GB (about 25 GPU-minutes) and on one RTX PRO 6000 96 GB (about 10 GPU-minutes), 8-13 timed steps per setting, with synthetic volumes replacing the restricted ADNI data.

**WHAT TO CHANGE**
- Skip the per-step gc.collect() and torch.cuda.empty_cache() calls (about 250 empty_cache calls per step; we neutralised them with a wrapper, no edit to your files): at batch 2, 64^3 the V100 goes 6.60 → 4.57 s/step (-31%); on the RTX PRO 6000 7.25 → 2.39 s/step, and the released 112^3 recipe 11.69 → 4.66 s/step.
- Run with ACCELERATE_MIXED_PRECISION=fp16 (default is fp32): V100 4.57 → 2.32 s/step (2.85x versus plain; appendix schedule 814 h → 286 h); RTX PRO 6000 recipe 4.66 → 3.29 s/step. No GradScaler and no loss-curve check, so numerics are NOT validated.
- Pin the patch size explicitly: RES_SCALE default 0.82 overrides the YAML 64^3 to 112^3, which OOMs a 32 GB V100 even at batch 1 (needs 70.7 GB on the RTX PRO 6000) → at 64^3, batch 1 runs at 3.98 s/step in 13.4 GB (batch 2: 26.6 GB).

**DELIVERABLES**
harness/bench_ae.py (hooks and timing driver), harness/bench_io.py (data-pipeline proxy), harness/run.sh, harness/run_pro6000.sh, harness/all_pro6000.sh (launch scripts) and the sandbox wrapper in harness/ (bwrap_*.sh); measurements/b64_plain.json, b64_nogc.json, b64_nogc_fp16.json, b64_b1.json, b64_stages.json, r80_nogc_fp16.json, io_64.json, io_112.json (timings), measurements/pro6000/ (RTX PRO 6000 timings), measurements/gpu_*.csv (GPU traces); timing table, config-gap table (section 6) and suggestions (section 7) in this report.

## 0. Read this first
The issue reporter measures about 3.2 s per training step on an A100 80 GB (batch 2, 64x64x64 patches) and projects "more than 10 days" for the paper's 300 epochs. We timed the authors' own Step-1 autoencoder training script, unmodified, on one Tesla V100 32 GB. The ADNI data is not public (data-use agreement), so the data loader was replaced with synthetic volumes; everything after the loader is their code.

Headline: at the reporter's setting (batch 2, 64^3) the released script costs 6.60 s/step on a V100. The appendix schedule (444,150 steps) is then about 34 days on a V100 and about 16.5 days on the reporter's A100 (their number). Two wrapper-level changes, no edits to the authors' files, bring the V100 to 2.32 s/step (2.85x), which is 11.9 days for the same schedule. The released recipe itself (60,000 steps, 112^3 patches) does not fit in 32 GB at all; on an RTX PRO 6000 96 GB it needs 70.7 GB and was measured at 11.69 s/step (8.1 days), 3.29 s/step (2.3 days) with the two changes (section 5b).

## 1. Pinned commit and exact environment
- Repo: github.com/chqwer2/Disease-Progression-World-Model, Apache-2.0 (LICENSE at root), commit `ac2ca4d8abb6f3434045260ff1a6b5f37459b5bb` (HEAD of main on 2026-10-15). Project used: "ICLR 2026 Delta-LFM", script `step1_v2_axes.py`.
- Host: our GPU host, 1x Tesla V100 32 GB (GPU 0 only), driver 580, `nice -n 10`, `taskset` to 8 CPUs, other CPUs busy with an unrelated 72-worker job (so CPU-side numbers are pessimistic).
- PRO 6000 addendum: a second GPU host, torch 2.8.0+cu128, MONAI 1.4.0, same commit, sandboxed as described in section 8.
- Python 3.12.3 venv; torch 2.5.1+cu124 (arch list includes sm_70), torchvision 0.20.1, MONAI 1.4.0, numpy 1.26.4, accelerate, torchmetrics, pytorch_msssim, lpips. No native extension had to be rebuilt.
- Deviations: synthetic loader (uniform-random volumes plus random ages/ids) instead of ADNI NIfTI; `--num_workers 0`; the end-of-run validation inside the script was left on; the MAISI VAE initial weights (`autoencoder_epoch273.pt`) and the AlexNet/LPIPS weights were downloaded at run time by MONAI/torchvision/lpips as the script does by design. Telemetry env off, `WANDB_MODE=disabled`.

## 2. What was run
Our harness (harness/bench_ae.py) loads the authors' script with `runpy`, swaps in a synthetic triplet loader, and hooks gc.collect, cuda.empty_cache, Tensor.backward, AdamW.step, MONAI PerceptualLoss / PatchAdversarialLoss and the MAISI encoder/decoder/discriminator forward calls. 3 warm-up steps, then 12-13 timed steps. The command line is the repo's `scripts/01_train_autoencoder.sh` (ArcRank on) with the data options replaced.
- Reporter setting: batch 2, 64^3 patch (YAML default), "plain" run, a "stages" run (CUDA-synchronised hooks), and variants.
- Recipe setting: `RES_SCALE` default 0.82 gives 112^3 patches, batch 1 (each sample is a triplet of three scans, so 3 volumes per step).
- Also run: a CPU-side proxy of the data pipeline (harness/bench_io.py, our replica of the MONAI transform chain on synthetic 121x145x121 volumes).
Not run: the full schedule, flow-matching stages 2-3, evaluation, the real ADNI/OASIS pipeline.

## 3. Where the time goes (batch 2, 64^3, V100 fp32, 6.6 s/step)
| Stage | s/step | share | note |
|---|---|---|---|
| backward (3 calls: generator, discriminator, extra terms) | 3.63 | 54% | |
| autoencoder forward (encode 0.61 + decode 1.00) | ~1.3-1.6 | ~22% | includes end-of-epoch validation calls that fell inside the window (1.23 calls/step), so true forward is a bit lower |
| `gc.collect()` (3 calls/step) | 1.19 | 18% | called every step by the script |
| `torch.cuda.empty_cache()` (about 250 calls/step) | 0.43 | 7% | |
| LPIPS perceptual loss | 0.05 | 1% | |
| discriminator, adversarial loss, AdamW | 0.04 | <1% | |
Stage times are CUDA-synchronised totals divided by timed steps; they overlap slightly with each other and with the validation call, so read shares as approximate. The measured proof that the housekeeping calls matter is the variant below (6.60 s to 4.57 s, -31%, more than the 1.6 s the hooks attribute, because freed cache must be re-allocated).

| Variant (batch 2, 64^3) | s/step | speed-up | peak alloc GB | note |
|---|---|---|---|---|
| released script, plain | 6.60 | 1.00x | 26.6 | measured |
| stages run (sync hooks) | 6.66 | | 26.6 | hooks cost <1% |
| skip gc.collect and empty_cache (wrapper no-op) | 4.57 | 1.44x | 26.6 | measured |
| + fp16 autocast via `ACCELERATE_MIXED_PRECISION=fp16` | 2.32 | 2.85x | 24.2 | measured speed; no GradScaler, numerics NOT validated |
| batch 1, 64^3, plain | 3.98 | | 13.4 | measured |
| 80x96x80 batch 1, skip gc + fp16 | 2.51 | | 28.3 | measured; plain fp32 at this size OOMs |
| 96x112x96 and 112^3 batch 1 (plain, and skip gc + fp16) | OOM | | >31 | measured: does not fit 32 GB |
Data loading proxy: 0.23 s per triplet at 64^3 and 0.34 s at 112^3 per CPU core (gzip vs raw within noise). Even at batch 2 with 4 workers that is hidden behind a 2-6 s GPU step, so data loading is not the bottleneck on this proxy (real ADNI file sizes and their augmentations may differ).

## 4. GPU utilisation and memory (measurements/gpu_*.csv, 0.5 s sampling)
Averages cover whole processes including start-up and validation, not just steps. Baseline plain run: 78% mean utilisation, 27.8 GB peak, 135 W. Skip-gc run: 86%, 168 W. fp16 run: 65% (shorter steps, more time in host work), 125 W. Batch 1: 71%, 14.2 GB. Oversize runs ended in OOM at 31.7 GB. Note the baseline's utilisation dips come from the synchronous gc/empty_cache calls.

## 5. Projection of their schedules
Appendix schedule as quoted in the issue: 300 epochs x 2,961 triplets / batch 2 = 444,150 steps at 64^3.
| Hardware / variant | s/step | hours | days | status |
|---|---|---|---|---|
| V100 32 GB, released script | 6.60 | 814 | 33.9 | measured step, projected total |
| V100, skip gc/empty_cache | 4.57 | 564 | 23.5 | measured step |
| V100, + fp16 autocast | 2.32 | 286 | 11.9 | measured step, numerics unvalidated |
| A100 80 GB (reporter) | 3.2 | 395 | 16.5 | reported by reporter |
| RTX 3090 (estimate) | 2.5-3.2 | 308-395 | 12.9-16.5 | estimate: assumes 0.8-1.0x A100 on this fp32/TF32 conv workload; 24 GB cannot hold batch 2 (26.6 GB) so batch 1 x 2 accumulation needed |
| RTX 4090 (estimate) | 1.6-2.1 | 197-259 | 8.2-10.8 | estimate: assumes 1.5-2.0x A100; same 24 GB limit |
Released recipe (`01_train_autoencoder.sh`): 30 epochs x 2,000 = 60,000 steps, batch 1, 112^3. It cannot run on 32 GB (measured OOM). Extrapolation by voxel count (linear fit of the 64^3 batch 1/2 points) gives about 15 s/step plain (about 257 h = 10.7 days) and about 4.2 s/step with the two changes (about 70 h), assuming it fit memory; low confidence, estimates only, and an 80 GB card is needed (fp16 peak was about 13 GB per million voxels, so about 55-60 GB).
The 4090 batch-4 / 30-day claim in other threads is a different repo; none of this was measured on a 3090/4090.

## 5b. Measured on RTX PRO 6000 96 GB (owner-approved addendum)
Same harness and unmodified authors' script, synthetic volumes, one RTX PRO 6000 Blackwell (second GPU host), torch 2.8.0+cu128 (sm_120), 8 CPUs at nice 10 while the a second GPU host load average was about 71 from another job. 8-12 timed steps per row after warm-up. All values below are MEASURED.
| Setting | PRO 6000 s/step | PRO 6000 peak VRAM (allocated) | V100 s/step (same code, torch 2.5.1) | V100 / PRO 6000 |
|---|---|---|---|---|
| released recipe 112^3, batch 1, fp32 | 11.69 | 70.7 GB | OOM at 32 GB | n/a |
| same + skip gc/empty_cache | 4.66 | 70.7 GB | OOM | n/a |
| same + skip gc + fp16 autocast | 3.29 | 64.3 GB | OOM | n/a |
| reporter 64^3, batch 2, fp32 | 7.25 | 26.6 GB | 6.60 | 0.91x |
| same + skip gc/empty_cache | 2.39 | 26.6 GB | 4.57 | 1.91x |
| same + skip gc + fp16 autocast | 1.50 | 24.2 GB | 2.32 | 1.55x |
Reading: with the per-step `gc.collect()` / `empty_cache()` left in, the PRO 6000 is no faster than the V100 (0.91x) because the step is dominated by host-side work on a contended CPU, not by the GPU. Once that is removed the PRO 6000 is 1.9x the V100 in fp32. This also suggests the reporter's 3.2 s on an A100 reflects a faster or idle host CPU; the housekeeping cost scales with CPU speed and heap size. Mean GPU utilisation over whole runs was 34-63% (measurements/pro6000/gpu_*.csv; includes start-up and validation). Min/max step times: 112^3 plain 8.4-13.4 s, nogc 4.4-5.6 s, nogc+fp16 2.8-3.7 s.
Measured peak VRAM actually reached 75.7 GB (nvidia-smi, includes allocator cache) against the 60 GB declared to the job scheduler; the lease was still granted because the card had 93 GB free, but the ask was low (note for future leases: declare about 80 GB for this recipe).

Schedules recomputed from the measured PRO 6000 steps (projection = measured step x steps):
| Schedule | variant | PRO 6000 hours | days |
|---|---|---|---|
| released recipe, 60,000 steps (112^3, batch 1) | plain | 194.8 | 8.1 |
| | skip gc | 77.7 | 3.2 |
| | skip gc + fp16 | 54.9 | 2.3 |
| appendix as quoted, 444,150 steps (64^3, batch 2) | plain | 893.9 | 37.2 |
| | skip gc | 295.1 | 12.3 |
| | skip gc + fp16 | 185.1 | 7.7 |
The earlier V100 extrapolation for 112^3 (about 15 s/step, 257 h plain; about 4.2 s, 70 h with changes) was an estimate only; it cannot be checked on 32 GB. The measured PRO 6000 values supersede it as the evidence for the recipe; the 3090/4090 rows in section 5 remain unmeasured estimates, and the 112^3 recipe cannot fit a 24 GB card in any variant we saw (>=64 GB).

## 6. Config-vs-paper gap table
| Item | Paper appendix (as quoted in issue) | Released script (HEAD ac2ca4d) |
|---|---|---|
| epochs / steps | 300 epochs (about 444k steps at batch 2) | 30 "epochs" x 2,000 steps = 60,000 steps (issue saw 6 epochs; repo changed on 2026-09-17) |
| batch size | 2 | 1 sample = triplet of 3 volumes |
| learning rate | 1e-3 | 1e-5 |
| patch size | 64^3 (reporter) | YAML says 64^3, but `RES_SCALE` default 0.82 overrides it to 112^3 |
| initialisation | reporter used random | MAISI pretrained VAE downloaded at first use |
| precision | not stated | `Accelerator()` with no mixed precision: fp32 unless an accelerate config sets it; explicit bf16 autocast only in side branches (bf16 is not native on V100) |
| per-step overhead | none stated | `gc.collect()` and `empty_cache()` every step |
| losses | not stated | Charbonnier, LPIPS (alex, 2D slices), PatchGAN adversarial (ramped after 400+1200 steps), ms-ssim, ArcRank/contrastive terms |

## 7. Suggestions (testable)
1. Remove the per-step `gc.collect()` / `torch.cuda.empty_cache()` - measured -31% on V100.
2. Use mixed precision (fp16 with GradScaler on V100; bf16 on A100/4090) - measured 2x further on V100 at the speed level; needs a loss-curve check.
3. Gradient checkpointing in the MAISI blocks to make 112^3 fit 32 GB - estimated, untested.
4. Run triplet members as micro-batches to fit a 24 GB card - estimated, untested.
5. Enable `torch.backends.cudnn.benchmark` and channels_last_3d - estimated, untested.
6. Publish the exact config behind the paper's 300-epoch run (steps/lr/patch/init) - the 60k-step released recipe cannot be the same experiment.

## 8. Ephemeral-run statement

Your code, weights and data were handled only in a throwaway, unprivileged account on a GPU host with no access to our other files. Everything we fetched or built was deleted when the run ended; only numbers and the small harness we wrote were kept. Nothing was posted or sent, and no one was contacted before this report.

## 9. What we could not run or verify
- No real ADNI/OASIS data (DUA); synthetic input means timings exclude real I/O and any data-dependent effects (the validation metrics printed are meaningless).
- fp16 variant has no GradScaler and no loss-quality check.
- The PRO 6000 rows were measured on a CPU-contended host (load about 71), so host-bound rows (plain) are pessimistic and noisy; no A100/3090/4090 measured; those rows are reported or scaled.
- Recipe-size (112^3) steps and the paper's exact configuration could not be run on 32 GB.
- Stages 2-3 (latent extraction, flow matching) not profiled.
- CPU contention from the neighbouring job may inflate host-side stages.

## 10. Files
REPORT.md, SUMMARY.md, measurements/ (timing json per run, gpu_*.csv traces, io_*.json), harness/ (bench_ae.py, bench_io.py, run.sh; our code only).

Accelerate everything.
