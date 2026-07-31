# Compute inventory and safety envelope

Hardware is captured again inside every run manifest. This file describes the
current scheduling pool, not a substitute for run-time evidence.

## Current inventory: 2026-07-30

| Host | Accelerator | VRAM | System RAM observed | Intended role |
|---|---|---:|---:|---|
| Lab workstation A | RTX 4090 | 24 GB | 94 GiB | Primary training/evaluation |
| Shared lab host B | RTX 3090 | 24 GB | shared 31 GiB | Ampere-compatible reproduction or judging |
| Shared lab host B | RTX PRO 6000 Blackwell | 96 GB | shared 31 GiB | Large/compatibility runs |

Unrelated services on shared hosts are outside this project's scope.

## Current shared-host rule

Only one experimental GPU process may run on a shared host at a time. The 3090
is part of the available compute pool, but it is not run concurrently with a
PRO 6000 training or judging job under the currently measured memory envelope.

Every shared-host experiment must:

- select the exact GPU UUID and verify the product name;
- run in its own user scope with explicit memory and CPU limits;
- use positive nice and low I/O priority;
- check available RAM before launch;
- leave unrelated services unchanged and outside the experimental cgroup;
- stop the experiment if safety limits are reached.

Concurrency is reconsidered only after a new read-only hardware and memory
inventory is captured. Existing manifests are never edited retroactively.
