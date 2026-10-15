# Profiling report: ECG digitization training time (GitHub issue rtmalikian/Kaggle-PhysioNet---Digitization-of-ECG-Images #2)

## 0 What we did for you

**WHAT WE DID**
Ran your real dataset class, model and trainer (train_ecg_model.py; MIT, commit 446f25dcbc62678a58dec5f2ae01d7ee0e900c9b) on one Tesla V100 32 GB for about 6 GPU-minutes (12-28 timed batches per setting) with a synthetic ECG image/signal tree, because the competition data was not downloaded.

**WHAT TO CHANGE**
- Change the hard-coded num_workers=0 in the full-dataset trainer to 4-8 (the comment is about M1 segfaults; it also applies on CUDA): 3.90 → 0.47 s/step with 4 workers (8x), 0.24 s/step with 8 workers + fp16; 10 epochs 81 h → 9.8 h (4 workers) or 4.9 h (8 workers + fp16), projected from the measured step.
- Replace the hard-coded bf16 autocast with fp16 on Volta GPUs (bf16 is emulated on V100; the GradScaler is only needed for fp16): GPU-only step 0.48 → 0.18 s (2.7x); end-to-end with 4 workers 0.47 → 0.40 s/step.
- Raise the batch size from 2 to 16 (peak memory only 12.6 → 13.6 GB because parameters and AdamW state dominate): GPU-only fp16 cost per image 0.09 s → 0.030 s (3x less).

**DELIVERABLES**
harness/bench_ecg.py (synthetic data builder and timing driver around your dataset class and trainer), harness/run8.sh (launch script); measurements/data.json, data2.json (loader cost), measurements/model_*.json (GPU-only step: fp32, bf16, fp16, batch 2/8/16), measurements/e2e_*.json (end-to-end with 0, 4, 8 workers, bf16 and fp16), measurements/gpu_*.csv (GPU traces); timing table, config-observation table and suggestions in this report.

## 0. Read this first
The issue reports that training on a 2021 M1 iMac takes 18-24 hours per epoch (100-200+ days in total), and proposes "use a cloud GPU (50-100x)". We ran the authors' real dataset class, model and trainer (`train_ecg_model.py`) on one Tesla V100 32 GB with a synthetic ECG image/signal tree (the Kaggle/PhysioNet competition data was not downloaded).

Headline: the training script as released costs 3.9 s per step (batch 2) on a V100, almost all of it in the single-process image loader (`num_workers=0`, about 0.8-1.1 s of CPU preprocessing per image). On the ~12,000-image training split that is about 6.5 h per epoch plus 1.6 h of validation: 8.1 h per epoch, i.e. a V100 is only 2.2-3x faster than the M1, not 50-100x. Four loader workers cut the step to 0.47 s (8x), and fp16 instead of the hard-coded bf16 cuts the GPU part from 0.48 s to 0.18 s. The model has 676 M parameters, not the "about 15 M" in the issue.

## 1. Pinned commit, licence, environment
- Repo github.com/rtmalikian/Kaggle-PhysioNet---Digitization-of-ECG-Images, MIT (LICENSE verified at clone time), commit `446f25dcbc62678a58dec5f2ae01d7ee0e900c9b`. Single-author competition repo, 0 stars.
- Host our GPU host, one Tesla V100 32 GB (index 2 only, by UUID), driver 580, `nice -n 15`, `taskset` to 8 CPUs (neighbouring labelling job), Python 3.12.3, torch 2.5.1+cu124 (sm_70), albumentations 1.3.1, opencv 4.x.
- Data terms: competition data (Kaggle / PhysioNet) not downloaded, so no terms were accepted. Synthetic stand-in: 30 patients, 2 images each of 1,700x2,200 px (grid plus drawn traces), 12-lead CSV of 5,000 samples. Real image sizes and file compressibility may differ, so the data-loader numbers are indicative.
- Deviations: synthetic data; for the precision variants a harness wrapper replaces the trainer's hard-coded bf16 autocast dtype by fp16 or by none; everything else is the authors' code.

## 2. What was run
`harness/bench_ecg.py` builds the synthetic tree, then (a) times the authors' `FullECGImageDataset.__getitem__` in one process; (b) runs `EnhancedECGTrainer.train_epoch` (their loop: autocast, GradScaler, clipping, AdamW, L1+MSE loss) on fixed synthetic tensors to isolate the GPU step; (c) runs the same loop fed by the real dataset class with 0, 4 or 8 loader workers. 12-28 batches per measurement, first 2 excluded.
Not run: the real data, evaluation/inference, the other pipeline scripts in the repo (`enhanced_run_ecg_digitization.py`, `src/training/*`), convergence.

## 3. Measurements (V100, batch 2 unless noted)
| Setting | s/step | note |
|---|---|---|
| GPU step only, bf16 autocast (the released code on CUDA) | 0.48 | bf16 is emulated on V100 |
| GPU step only, fp16 autocast | 0.18 | 12.6 GB peak |
| GPU step only, fp32 (no autocast) | 0.17 | 12.6 GB peak |
| GPU step only, fp16, batch 8 / batch 16 | 0.29 / 0.48 | 12.6 / 13.6 GB; 0.036 / 0.030 s per image vs 0.09 at batch 2 |
| end-to-end, `num_workers=0` (released), bf16 | 3.90 | loader-bound |
| end-to-end, 4 workers, bf16 | 0.47 | loader-bound |
| end-to-end, 4 workers, fp16 | 0.40 | loader-bound |
| end-to-end, 8 workers, fp16 | 0.24 | loader-bound |
Loader cost per image in one process: about 0.8-1.1 s (decode 1,700x2,200 PNG, albumentations pipeline, resize to 512x512; a first pass was 3.8 s on cold, contended CPUs); CSV read of 12 leads x 5,000 samples is 0.03 s. GPU utilisation during end-to-end runs was 12% with 0 workers and 46-83% with 4-8 workers (measurements/gpu_*.csv, covers start-up). The model has 676.0 M parameters; one Linear(262,144 -> 2,048) layer alone holds 537 M of them (the flattened 256x32x32 feature map), plus 12 per-lead generator heads of up to 10,000 outputs.

## 4. Projection of an epoch and a 10-epoch run
Assumptions: the issue's "about 15,000 images per epoch"; the script's 80/20 train/validation split (12,000 / 3,000 images); batch 2 (6,000 train + 1,500 validation steps); 10 epochs (script default; the issue wants 50-100).
| Setting | per epoch | 10 epochs | status |
|---|---|---|---|
| M1 iMac (reported in the issue) | 18-24 h | 7.5-10 d | reported |
| V100, released settings (0 workers, bf16) | 8.1 h | 3.4 d | measured step, projected |
| V100, 4 workers, bf16 | 0.98 h | 9.8 h | measured step, projected |
| V100, 8 workers, fp16 | 0.49 h | 4.9 h | measured step, projected (loader-bound) |
| V100, GPU only (loader free), fp16, batch 2 | 0.38 h | 3.8 h | lower bound from the GPU-only step |
| RTX 3090 / 4090 (estimate) | same as V100 while the loader is the limit; GPU-only fp16 step 2-3x faster | | ESTIMATE: assumes 1.4-2.3x (3090) and 2-3x (4090) V100; not measured |
The 50-100x gain promised by a cloud GPU is not available from the GPU alone: the step is 88-95% loader time on this code.

## 5. Config observations (code only; no paper)
| Item | Finding |
|---|---|
| model size | 676 M parameters (537 M in one fully connected layer); the issue and the docs describe a 15 M-parameter U-Net, but the training script contains a CNN encoder with a huge flatten layer, and its output heads emit 12 x 10,000 values per image |
| loader | `num_workers=0` is hard-coded in the full-dataset trainer, with a comment about segmentation faults on M1; it applies on CUDA too |
| precision | on CUDA the trainer uses bf16 autocast with a (float16-style) GradScaler; bf16 is emulated on Volta (2.7x slower than fp16 here) and the scaler is unnecessary for bf16 |
| batch | default 2; peak memory is 12.6 GB because parameters and AdamW state dominate, so batch 16 fits at 13.6 GB and costs 3x less per image |
| evaluation | 80/20 split uses `augment=True` for validation images too (the same dataset object), adding augmentation cost and noise |
| pipelines | several overlapping training/inference pipelines exist (`src/training`, `enhanced_run_ecg_digitization.py`); we only profiled the one the docs name |

## 6. Suggestions
Measured: use 4-8 loader workers (8x); switch to fp16 or fp32 on Volta (2.7x on the GPU part); batch 8-16 (3x per image).
Estimated / untested: cache the 512x512 preprocessed tensors once (the 1,700x2,200 decode dominates and repeats every epoch, giving a GPU-bound run of about 4 h for 10 epochs on a V100); replace the 537 M-parameter flatten-and-linear stage with global pooling or a conv head, which would cut parameters by about 100x; verify whether the small-U-Net described in the docs is the intended model.

## 7. Ephemeral-run statement
All of their code ran only on our GPU host as an unprivileged account (history off, telemetry env off, no access to the work directory), on V100 index 2 only, inside `the work directory`, which was removed at the end (only that directory; the shared work folder and other users' files were not touched) and verified gone. Nothing of theirs was copied out; only numbers left. Source was inspected with grep/sed; small excerpts viewed during analysis are summarised, not reproduced. Nothing was posted or sent; no one was contacted. About 6 GPU-minutes used.

## 8. What we could not run or verify

Your code, weights and data were handled only in a throwaway, unprivileged account on a GPU host with no access to our other files. Everything we fetched or built was deleted when the run ended; only numbers and the small harness we wrote were kept. Nothing was posted or sent, and no one was contacted before this report.

## 9. Files
REPORT.md, SUMMARY.md, measurements/ (json per run, gpu_*.csv), harness/ (bench_ecg.py, run8.sh; our code only).

Accelerate everything.
