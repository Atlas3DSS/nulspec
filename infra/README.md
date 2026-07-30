# Dev-box llama routes

The dev box is `wtatum84` / `192.168.1.90`.

| Physical GPU | UUID | Route | Port |
|---|---|---|---:|
| RTX 3090 | `GPU-caf6a1ca-616a-3427-7833-157477cd59f6` | `start_llama_3090` | 8080 |
| RTX PRO 6000 Blackwell | `GPU-d739b9c5-bfbb-e95a-bbf1-7122f38c2cf1` | `start_llama_pro6000` | 8081 |

From the workstation:

```bash
start_remote_llama_pro6000
stop_remote_llama_pro6000
start_remote_llama3090
stop_remote_llama3090
start_llama_both_remote
stop_llama_both_remote
```

`start_remote_llama4090` remains as a compatibility alias, but now starts the
RTX PRO 6000 route and prints a warning.

The mixed Ampere/Blackwell system enumerates cards differently in
`nvidia-smi` and CUDA. The launchers therefore select by GPU UUID and verify the
expected product name before starting. The Pro route uses the separate
`build-cuda-pro6000` binary compiled for `sm_120a`; the former `sm_86/sm_89`
binary could identify Blackwell but failed at its first kernel launch.

The launcher defaults to 8 CPU threads, nice level 10, lowest best-effort I/O
priority, and refuses to start below 10 GiB available system RAM. Those
guardrails protect the Palworld server. The 3090 route continues to use the
older Ampere build.

The exact files deployed to the dev box are retained under
`remote_payload/`. Pre-change copies on the dev box use the suffix
`.pre-pro6000-20260730`.

To rebuild the Pro binary without starving Palworld:

```bash
ssh wtatum84
cd ~/dev_genius/experiments/overnight_wierd
systemd-run --user --scope \
  -p MemoryHigh=6G -p MemoryMax=8G -p CPUQuota=600% \
  nice -n 15 ionice -c 2 -n 7 \
  bash infra/build_llama_pro6000.sh
```
