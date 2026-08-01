# Execution and resource log

This file records operational decisions that can affect reproducibility while
keeping them separate from scientific outcomes. Raw terminal logs and stage
checkpoints remain under the ignored `outputs/` tree.

## Compute allocation

| Frozen seed | Host | GPU | CPU allocation | Loader workers | Priority |
|---:|---|---|---|---:|---|
| 0 | workstation | GeForce RTX 4090, 24 GiB | default host scheduling | 6 | normal |
| 1 | dev box | RTX PRO 6000 Blackwell, 96 GiB | logical CPUs 8–15 | 6 | `nice 5` |
| 2 | dev box | GeForce RTX 3090, 24 GiB | logical CPUs 16–23 | 6 | `nice 5` |
| 3 | dev box | RTX PRO 6000 Blackwell, 96 GiB | logical CPUs 0–7 | 2, then 6 | `nice 10` |
| 4 | dev box | GeForce RTX 3090, 24 GiB | logical CPUs 24–31 | 2, then 6 | `nice 10` |

Seeds 3 and 4 share their GPUs with seeds 1 and 2. This changes throughput but
not the frozen algorithm: every seed remains a separate process, data split,
model initialization, optimizer, checkpoint tree, and prediction file. The
models occupy little VRAM, so independent concurrent trials use otherwise idle
device capacity without changing batch size, precision, or training code.

The workstation used PyTorch 2.9.1 with CUDA 13.0 wheels. The dev-box trials
used PyTorch 2.9.1 with CUDA 12.8 wheels. Every `config.json` captures the
actual host, GPU, compute capability, Python, Torch, CUDA, cuDNN, and NumPy
versions. GPU type is treated as a nuisance variable; upstream code does not
enforce deterministic CUDA algorithms, so cross-architecture bit identity is
not claimed.

Each extension reused its base seed's host, physical GPU, CPU set, split, and
saved checkpoints. Validated follow-on wrappers waited for the exact base
parent to exit and required that seed's atomic `complete.json` before starting;
the common-probe Hessian job was similarly queued only after the extension
wrapper completed successfully. This kept otherwise idle cards occupied
without allowing an incomplete base stage into downstream analysis. The local
seed-0 follow-on used the same boundary checks but did not need a shared-host
service guard.

## Resume event

Seeds 1 and 2 initially used two loader workers. After all three weak-teacher
stages and the ASR stage had completed, their first student stages were
interrupted intentionally to increase loader workers from two to six. The
student stages had not written stage checkpoints and restarted from epoch 0.
Completed teacher and ASR checkpoints were hash-preserved and reused. Loader
worker count affects input throughput only here because preprocessing has no
random augmentation; the model and sampler seeds are reset at every training
stage. Both the initial and resumed attempts remain in `run.log`.

The base runner rewrites its single config and split files on process restart,
so each final `config.json` records the resumed six-worker launch rather than
serving as an append-only attempt history. The initial two-worker launches and
exact restart boundaries are retained in the logs and this operations record;
the recreated splits were byte-identical and the final analyzer revalidated
their complete partitions. A future runner must instead write immutable
per-attempt launch manifests and reject resume drift outside prospectively
allowed throughput-only fields.

Seeds 3 and 4 began with two workers to establish a conservative shared-host
memory profile. A 12-second device sample during their first student stage
showed only 1–23% streaming-multiprocessor utilization while every loader
worker was CPU-saturated and more than 21 GiB remained available. A validated
watcher waited for each first student checkpoint and sent `SIGINT` only to the
newly started next stage. Both Python parents remained alive past the watcher's
30-second conservative limit, so it correctly refused a stronger automatic
signal. The operator then revalidated each exact command, process tree,
protected-service process, RAM margin, and GPU temperature; sent `SIGTERM` to
the validated parent; confirmed its whole seed process tree exited; and
relaunched from the completed boundary with six workers on the same eight-core
set. Four partial iterations for seed 4 and five for seed 3 had no checkpoint
and were discarded by the existing stage-level resume rule. The resumed stage
reset all model and sampler seeds. No completed stage or metric was altered,
and this throughput adjustment was decided without inspecting model outcomes.

## Shared-host safeguards

The dev box also ran a protected user service outside the experiment. The
replication neither signaled nor reconfigured that service. A fail-closed guard
checked every ten seconds and would send `SIGINT` only to a validated
`run_trial.py --seed N` parent if any of these conditions occurred:

- the protected service process disappeared;
- available system RAM fell below 8 GiB; or
- either experiment GPU reached 88 °C.

Additional seeds were launched only after at least 16 GiB was available. CPU
sets were disjoint and lower-priority jobs used `nice 10`. The guard validates
both the exact script path and seed argument before signaling; it cannot target
an unrelated PID merely because a PID file exists. No guard trip occurred
during the recorded run or any follow-on.

The extension and Hessian follow-ons apply the same 8 GiB/88 °C/service-health
conditions before launch and throughout execution. Their wrappers additionally
validate the exact downstream script path and seed before sending any signal.

## Checkpoint and failure semantics

Each stage writes one checkpoint only after the stage finishes, then the trial
writes `predictions.pth`, `results.json`, and finally `complete.json`. A missing
`complete.json` is never counted as a trial. Resumption skips only finished
stage checkpoints; partial epochs are discarded. All five frozen seeds are
required for the primary aggregate, and unfavorable or high-variance seeds are
not excluded.

Final per-stage and end-to-end wall times are derived from the checkpoint
payloads and retained logs after completion, rather than estimated from GPU
marketing throughput.

## Completion accounting

The primary five-seed execution window ran from 01:39:46 to 06:27:14 PDT on
2026-08-01: **4.791 hours of observed wall time**. The complete compute window,
including prospectively specified and post-hoc diagnostics, ended at 08:19:03
PDT: **6.655 hours of observed wall time**. These endpoints come from the
preserved config/completion file times and are operational observations, not a
GPU-utilization integral.

Runner-reported stage wall times sum to **28.074 device-process hours**:
18.137 primary training, 5.182 preregistered extensions, 0.003 common-probe
Hessian estimation, and 4.752 post-hoc loss-contract training. Concurrent
processes sharing one physical GPU are counted separately in that sum, so it
must not be described as either elapsed wall time or measured GPU-active time.

## Executed-code identity

All base processes loaded `run_trial.py` with SHA-256 `78987333...a661e0`.
After launch, Ruff reformatted the tracked copy to SHA-256
`81c8925b...3fd66`; local and remote AST dumps excluding source-location
attributes have the identical SHA-256 `f9644123...8604f`. No running process
reloaded the file, and no semantics changed. Both byte identities and the AST
identity are retained in `results/executed_code_manifest.json`. The extension
runner was synchronized before execution and is byte-identical across hosts.

## Publication sanitization

The executed shared-host orchestration copies necessarily contained the live
experiment root, interpreter path, and physical GPU UUIDs. The published shell
templates replace only those values with required environment inputs:
`REPLICATION_BASE`, `REPLICATION_PYTHON`, `PRIMARY_GPU_UUID`, and
`SECONDARY_GPU_UUID`. `PROTECTED_PROCESS_PATTERN` was already an environment
input and remains so. Exact executed and published shell hashes are paired in
`results/executed_code_manifest.json`; the process-validation, memory,
temperature, signaling, and stage-boundary logic is unchanged. Running jobs
continued from their already-loaded remote copies and did not reload the
publication templates.
