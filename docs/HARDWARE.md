# Compute inventory and safety envelope

Hardware is captured again inside every run manifest. This file describes the
current scheduling pool, not a substitute for run-time evidence.

## Current inventory: 2026-07-30

| Host | Accelerator | VRAM | System RAM observed | Intended role |
|---|---|---:|---:|---|
| Workstation (`MonkeyPC`) | RTX 4090 | 24 GB | 94 GiB | Primary training/evaluation |
| Dev box (`wtatum84`) | RTX 3090 | 24 GB | shared 31 GiB | Ampere-compatible reproduction or judging |
| Dev box (`wtatum84`) | RTX PRO 6000 Blackwell | 96 GB | shared 31 GiB | Large/compatibility runs |

The dev box also runs the Palworld service. It is not part of this project.

## Current dev-box rule

Only one experimental GPU process may run on the dev box at a time. The 3090 is
part of the available compute pool, but it is not run concurrently with a PRO
6000 training or judging job while system RAM is limited.

Every dev-box experiment must:

- select the exact GPU UUID and verify the product name;
- run in its own user scope with explicit memory and CPU limits;
- use positive nice and low I/O priority;
- check available RAM and Palworld activity before launch;
- leave Palworld unchanged;
- stop the experiment if safety limits are reached.

## Planned upgrades

The owner expects both systems to reach approximately 128 GB system RAM. This is
planning information only. Concurrency is reconsidered after the upgrade is
physically installed and a new read-only inventory is committed. No existing
manifest is edited retroactively.
