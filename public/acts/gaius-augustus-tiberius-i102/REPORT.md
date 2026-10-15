# Profiling report: Tiberius issue #102 (GPU out of memory in evidence workflow)

## 0 What we did for you

**WHAT WE DID**
Ran your released Tiberius CNN/bLSTM core and HMM block construction (MIT, commit 2562badaba40f1fbaf76cb3046d09e6cab24aef5, package 2.0.9, random weights) on one Tesla V100-PCIE-32GB with synthetic 500,040-base batches (1-5 timed forwards per batch size, TensorFlow 2.17.1); no pretrained weights or real data were downloaded and the full evidence pipeline was not run.

**WHAT TO CHANGE**
- Set tiberius.max_parallel: 1 in the Paludamentum params file (default unlimited; TensorFlow maps nearly all GPU memory per process): one worker at batch 4 uses 16.4 GiB per nvidia-smi (9.75 GiB TensorFlow peak), so two overlapping workers cannot share a 24 GB card; the cudaSetDevice failure itself was not reproduced.
- Set tiberius.batch_size: 4 and tiberius.seq_len: 500040 (your log shows Auto-computed batch_size=8 and seq_len=500040 despite --batch_size 4 --seq_len 4000000, so the outer flags did not reach the worker): TensorFlow peak 18.98 GiB → 9.75 GiB (nvidia-smi 24,334 → 16,796 MiB), forward 4.39 s per 8-sequence batch → 3.75 s per 4-sequence batch.
- Set NXF_SINGULARITY_CACHEDIR to a persistent directory so the container image is not downloaded again for each work directory (documented by Paludamentum; effect not measured here).

**DELIVERABLES**
harness/bench_tiberius_core.py (synthetic-input benchmark of the pinned model core and HMM block); measurements/b1_500040_growth_hmm_5steps.json, b2_500040_growth_hmm.json, b4_500040_growth_hmm.json, b8_500040_hmm_cap24g.json (per-batch timings and memory), measurements/tf220_cudnn_failure.json (TensorFlow 2.20.0 Conv1D failure on V100); timing table and config-gap table in this report.

## 0. Read this first

The public issue reports that standalone Tiberius works at batch 8 on a 24 GB RTX 4090, while the RNA-Seq + protein evidence workflow fails in TensorFlow `cudaSetDevice()` before prediction begins. The failure is consistent with multiple TensorFlow workers starting on one GPU: TensorFlow's documented default is to map nearly all visible GPU memory, and current Paludamentum documentation leaves `tiberius.max_parallel` unlimited unless configured. This is a strong, source-supported explanation, not a reproduced multi-process failure. [Issue #102](https://github.com/Gaius-Augustus/Tiberius/issues/102), [TensorFlow GPU memory guide](https://www.tensorflow.org/guide/gpu), [Paludamentum parameters](https://github.com/Gaius-Augustus/Paludamentum/blob/main/docs/parameters.md).

On the assigned V100, a synthetic batch of four 500,040-base sequences ran through Tiberius's CNN/bLSTM core in a median 3.75 s. TensorFlow reported a 9.75 GiB active-memory peak; `nvidia-smi` showed 16.4 GiB in use during the timed loop. The HMM block constructor corresponding to the issue's stack frame took 0.35–0.43 s in the growth-mode runs. These timings exclude trained weights, HMM decoding, real sequence parsing, and the rest of the evidence pipeline.

The actionable settings for a single-GPU Paludamentum run are `tiberius.max_parallel: 1`, `tiberius.batch_size: 4`, and `tiberius.seq_len: 500040`. The issue log's `Auto-computed batch_size=8` and `seq_len=500040`, despite the outer command specifying batch 4 and sequence length 4,000,000, shows those values did not reach the worker as intended. Current Paludamentum exposes these nested parameters and documents the concurrency cap. The 4,000,000 value also exceeds Tiberius's documented 500,040 limit. [Parameters](https://github.com/Gaius-Augustus/Paludamentum/blob/main/docs/parameters.md), [Tiberius README](https://github.com/Gaius-Augustus/Tiberius/blob/main/README.md).

## 1. Pinned commit, licence, environment

- Repository: [Gaius-Augustus/Tiberius](https://github.com/Gaius-Augustus/Tiberius). Authenticated `gh api repos/Gaius-Augustus/Tiberius --jq .license.spdx_id` returned `MIT` before cloning. Pinned commit: [`2562badaba40f1fbaf76cb3046d09e6cab24aef5`](https://github.com/Gaius-Augustus/Tiberius/commit/2562badaba40f1fbaf76cb3046d09e6cab24aef5), branch `main`, dated 2026-10-05; package version 2.0.9.
- Paper: Gabriel et al., “Accurate ab initio gene prediction in eukaryotes with Tiberius in multiple clades,” bioRxiv 2026, DOI [10.64898/2026.04.24.720536](https://www.biorxiv.org/content/10.64898/2026.04.24.720536v1), CC BY 4.0 per the preprint page. Its reported GPU speed comparison concerns ab initio prediction, not the evidence workflow in issue #102.
- Host: our GPU host, an unprivileged account; Tesla V100-PCIE-32GB, UUID `GPU-725106e3-11df-e1fc-003e-99f071a4e353`, driver 580.178.04. Only this UUID was exposed to the benchmark. Commands used `nice -n 10 taskset -c 24-31`; the batch-8 run had a TensorFlow 24,000 MB logical-device cap.
- Python 3.12.3, TensorFlow 2.17.1, CUDA 12.3/cuDNN 8.9.7 wheels. The repo permits TensorFlow 2.17–2.20. A first synthetic Conv1D attempt with TensorFlow 2.20.0 failed on this V100 (`No algorithm worked`, cuDNN status 5003); the same model ran with 2.17.1. This is an environment compatibility result, not evidence that 2.20 fails on the reporter's RTX 4090.
- The README/model configuration documentation provides public model archive URLs but no separate weights-use terms. No pretrained weights, genome, RNA-Seq, protein, or other biological data were downloaded. The benchmark used random initialization and synthetic tensors instead. The repository's issue owner appears to be an academic research group, but its legal contracting status was not independently established.

## 2. What was run

The harness imports the pinned repository's `tiberius.models.lstm_model`, `tiberius.hmm.HMMBlock`, and `tiberius.main.compute_auto_batch_size`. It constructs the HMM block used by `PredictionGTF.load_model`, then runs the actual Tiberius CNN/bLSTM on synthetic float tensors shaped `[batch, 500040, 5]`. Model settings use the documented Insecta `units=186`; other dimensions are the `lstm_model` source defaults. Weights are random. There was one warm-up and three timed forwards per batch (batch 1 used two warm-ups and five timed forwards). Timing synchronized on tensor output.

Batches 1, 2, and 4 used TensorFlow memory growth to expose the model's active allocation. Batch 8 used a 24,000 MB logical-device cap to stay within the assigned VRAM budget. HMM initialization was included, but the HMM Viterbi decode was not run. No trained-weight model, FASTA-based CLI prediction, Singularity image, Nextflow evidence tasks, or real reads/proteins were run.

The current Tiberius README says the evidence pipeline is in the separate Paludamentum Nextflow repository. Paludamentum documents `tiberius.max_files: 20` and `tiberius.max_parallel: unlimited` by default, and explicitly suggests `max_parallel: 1` for a single-GPU workstation. Its nested `tiberius.batch_size` and `tiberius.seq_len` values are forwarded into `tiberius.py`. [Paludamentum README](https://github.com/Gaius-Augustus/Paludamentum/blob/main/README.md), [parameters](https://github.com/Gaius-Augustus/Paludamentum/blob/main/docs/parameters.md).

## 3. Where the time goes

| Measured component | Result | Scope |
|---|---:|---|
| HMM block construction | 0.35–0.43 s in growth-mode runs; one capped run took 1.52 s | Startup only; includes the TensorFlow HMM object initialization |
| CNN/bLSTM forward, batch 1 | 2.045 s median | One 500,040-base batch |
| CNN/bLSTM forward, batch 2 | 3.405 s median | Two sequences per batch |
| CNN/bLSTM forward, batch 4 | 3.755 s median | Four sequences per batch |
| CNN/bLSTM forward, batch 8 | 4.392 s median | Eight sequences; 24,000 MB TensorFlow cap |

The batch-4 run had a 10,468,480,768-byte TensorFlow active-memory peak (9.75 GiB) and 16,796 MiB reported by `nvidia-smi` during the timed loop. Batch 8 had a 20,383,506,944-byte TensorFlow active-memory peak (18.98 GiB); its capped run showed 24,334 MiB allocated by `nvidia-smi`. TensorFlow's active-memory statistic excludes some allocator-reserved memory, so both numbers are retained rather than treated as interchangeable. [TensorFlow memory-stat API](https://www.tensorflow.org/api_docs/python/tf/config/experimental/get_memory_info).

In the issue trace, the error occurs while TensorFlow initializes a CUDA context from the HMM construction path, before it reaches a prediction step. Reducing a batch can reduce model working memory after startup, but cannot make a second process's initial GPU reservation fit beside a first process that already claimed the device. TensorFlow documents that default behavior and the `set_memory_growth` alternative. The Tiberius source inspected here does not configure memory growth itself.

## 4. Variants (V100)

| Variant | Median forward time | TensorFlow active peak | `nvidia-smi` during loop | Status |
|---|---:|---:|---:|---|
| Batch 1, growth | 2.045 s | 2.50 GiB | 6,508 MiB | Measured, 5 steps |
| Batch 2, growth | 3.405 s | 4.98 GiB | 12,668 MiB | Measured, 3 steps |
| Batch 4, growth | 3.755 s | 9.75 GiB | 16,796 MiB | Measured, 3 steps |
| Batch 8, 24,000 MB cap | 4.392 s | 18.98 GiB | 24,334 MiB | Measured, 3 steps; at the cap |
| TensorFlow 2.20.0, batch 1, 50,040 bases | — | — | — | Failed before timing in cuDNN Conv1D; see `measurements/tf220_cudnn_failure.json` |

The batch-8 result shows that this random-weight core can execute within a 24 GB TensorFlow limit on a V100. Its observed allocator footprint is close to the limit and leaves little room for co-scheduled TensorFlow processes or additional stages. This does not establish that the full trained model plus HMM decoding fits on an RTX 4090.

## 5. Projection

For `N` synthetic 500,040-base sequences on this V100, the measured batch-4 CNN/bLSTM estimate is `3.755 × ceil(N / 4)` seconds if one process runs batches serially. For example, 20 such sequences would take about 18.8 seconds for this model-forward portion. **ESTIMATE:** it excludes HMM decoding, input/output, real model weights, evidence processing, and task startup; it is not a whole-genome or whole-pipeline estimate. The issue does not provide enough genome-size and task-trace information for a full duration projection.

No RTX 4090 estimate is presented as measured. The reporter's standalone batch-8 success is an issue report, not a measurement from this run.

## 6. Config-vs-paper gap table

| Item | Paper / docs | Pinned code or issue evidence |
|---|---|---|
| Scope | 2026 paper benchmarks Tiberius ab initio gene prediction across clades and compares with other predictors. | Issue #102 runs the separate Nextflow evidence pipeline with four RNA-Seq libraries and proteins. Paper throughput does not specify that workload. |
| Pipeline location | Tiberius README points to Paludamentum for Nextflow and extrinsic evidence. | Current Tiberius launcher marks legacy Nextflow flags as removed; current Paludamentum owns evidence orchestration. |
| GPU task concurrency | Paludamentum parameters list `tiberius.max_files: 20` and `tiberius.max_parallel: unlimited` by default; the docs suggest `1` for a single-GPU workstation. | Multiple workers on one 24 GB GPU are consistent with the issue's `cudaSetDevice()` startup failure. This overlap was not reproduced. |
| Batch override | Tiberius standalone accepts `--batch_size`; Paludamentum exposes `tiberius.batch_size` and forwards it to worker `tiberius.py`. | The issue's worker log says `Auto-computed batch_size=8`, so the outer `--batch_size 4` was not effective for that worker. Set the nested pipeline parameter and confirm the task log. |
| Sequence length | Tiberius warns that values above 500,040 can hit a TensorFlow error; Paludamentum exposes `tiberius.seq_len`. | The issue requested 4,000,000 but logged 500,040. Use 500,040 or the documented default and verify the worker command. |
| GPU sizing | Tiberius auto-batch code scales from total GPU memory and uses `nvidia-smi`; it does not use currently free VRAM. | At 500,040 bases, the repo helper selects batch 8 for both 24 GB and 32 GB inputs. This does not account for competing tasks. |
| TensorFlow allocation | TensorFlow defaults to mapping nearly all memory on visible GPUs; memory growth is an available runtime option. | Tiberius source does not enable growth. This makes per-GPU task serialization the simplest supported first test; growth would require a runtime/container change. |
| Model/weights | The paper and repo provide pretrained models; the model config README names public weight URLs but no separate terms were listed there. | We avoided those weights and used random initialization, so this is a compute profile, not an accuracy or full prediction reproduction. |
| Container cache | Paludamentum images are cached under its Singularity cache; `NXF_SINGULARITY_CACHEDIR` selects a persistent cache location. | The issue's repeated image download across work directories can be addressed by setting that environment variable to a shared persistent directory. |

Sources: [paper](https://www.biorxiv.org/content/10.64898/2026.04.24.720536v1), [Tiberius README](https://github.com/Gaius-Augustus/Tiberius/blob/main/README.md), [Paludamentum README](https://github.com/Gaius-Augustus/Paludamentum/blob/main/README.md), [Paludamentum parameters](https://github.com/Gaius-Augustus/Paludamentum/blob/main/docs/parameters.md), [TensorFlow GPU guide](https://www.tensorflow.org/guide/gpu).

## 7. Suggestions

1. **Measured recommendation:** For a single 24 GB GPU, set `tiberius.max_parallel: 1` and `tiberius.batch_size: 4` in the Paludamentum params file. Set `tiberius.seq_len: 500040` (not 4,000,000). These exact parameters are documented by current Paludamentum. The V100 batch-4 core ran at 3.75 s with 9.75 GiB TensorFlow active peak and 16.4 GiB in `nvidia-smi`; the reporter's RTX 4090 behavior remains unmeasured.
2. **Measured diagnostic:** Check the task's `.command.sh` and `.command.err` or merged `params.yaml`. If the worker still logs `Auto-computed batch_size=8`, then the batch override still is not reaching Tiberius. A direct `tiberius.py` flag is different from the pipeline's nested `tiberius.batch_size` parameter.
3. **Estimated cause/fix:** Limiting Tiberius to one concurrent process per GPU should prevent multiple TensorFlow workers from competing for the same device context. If single-worker batch 4 still fails, inspect current free VRAM and use the worker's real log to distinguish startup reservation from prediction-time OOM. Do not infer the cause from batch size alone.
4. **Measured runtime compatibility:** On this V100, TensorFlow 2.17.1 worked; 2.20.0 did not execute the Conv1D kernel. Pin a V100-compatible TensorFlow/cuDNN combination in the container and validate on the actual target GPU before updating a published image. The compatibility failure may be hardware-specific.
5. **Docs-supported cache option:** Set `NXF_SINGULARITY_CACHEDIR` to a persistent directory accessible to the submit host and compute nodes. Paludamentum documents this cache mechanism; no separate direct-image-path option was verified for the issue's historical launcher.
6. **Untested runtime change:** If serialization is insufficient and several workers must share one GPU, enable TensorFlow memory growth before any TensorFlow operation in the container. The benchmark used growth for batches 1–4, but did not modify or validate the production image or multi-process workflow.

## 8. Ephemeral-run statement

Your code, weights and data were handled only in a throwaway, unprivileged account on a GPU host with no access to our other files. Everything we fetched or built was deleted when the run ended; only numbers and the small harness we wrote were kept. Nothing was posted or sent, and no one was contacted before this report.

## 9. What we could not run or verify

- The full Paludamentum Nextflow workflow with four RNA-Seq libraries and protein evidence, because those inputs were not supplied and their terms were not verified.
- Full Tiberius CLI prediction with trained weights and a FASTA genome; the weight archive's separate terms were not documented in the model configuration README, so it was not downloaded.
- HMM Viterbi decoding, end-to-end output generation, or the CPU-side evidence steps.
- The reported multi-worker overlap and `cudaSetDevice()` failure on the reporter's RTX 4090. The concurrency explanation is inferred from issue traceback, current pipeline defaults, and TensorFlow's allocation behavior.
- The RTX 4090 timing and memory numbers, the reporter's exact Paludamentum version/config, the number of GPU tasks launched, and a whole-genome duration.
- Whether `Gaius-Augustus` is a contracting legal entity; public affiliations look academic, but no legal status was independently confirmed.

## 10. Files

- `SUMMARY.md` — scheduler summary, marked NOT SENT.
- `REPORT.md` — this report.
- `harness/bench_tiberius_core.py` — synthetic-input benchmark harness.
- `measurements/` — per-variant JSON and the TensorFlow 2.20.0 cuDNN failure summary.

Accelerate everything.
