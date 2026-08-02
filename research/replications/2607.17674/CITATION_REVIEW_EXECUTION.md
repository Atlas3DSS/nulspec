# Citation-review execution record

## Attempt `20260802T061712Z-pro6000-full-offload`

The preregistered six-source Qwen calibration began on the dev-box RTX PRO
6000 while the first paper-faithful factorization arm was still training on the
same GPU. This is an operational departure from the runbook's idle-GPU
precondition. It does not change any citation prompt, evidence packet, schema,
sampling parameter, model weight, or primary experiment configuration. The
reason was an explicit operator decision to use otherwise free PRO 6000 VRAM
while preserving capacity for unrelated non-experimental services. This
attempt does not relax the repository's one-experimental-GPU-workload-per-host
policy; the concurrency departure is retained here as a process deviation.

The citation runner uses a separate clean checkout at commit
`2a0ad3c643eff53e06fdab6567cd0a3b5858eea2`; no file in the active primary-run
checkout is updated while that arm is live. The frozen packet was copied
without deletion and its deterministic path/size inventory matched at source
and destination (`aa90d03907c068ea69d58cb956a93499b32b9afdb2bf5a066d18671e09e917d2`).
The packet validator independently confirmed 41 sources, 74 occurrences, 112
chunks, and 4,230,676 source-text bytes on the execution host.

The reviewer is the registered 16,547,400,352-byte GGUF with SHA-256
`b62cbed05de4b9e368a19cf0dd575a43bedd0546920a6e31a812e34ff67299e9`.
The native Blackwell llama-server is version 8942 at upstream commit
`f53577432541bb9edc1588c4ef45c66bf07e4468`; its executable SHA-256 is
`6971bf707e72339bc758e5370a88e2a3cee5f3f73eaa2458e8f23fec2e45301b`.
The route retains the registered 50,000-token context, full GPU offload, flash
attention, one slot, f16 KV cache, batch 2,048, microbatch 512, and eight CPU
threads. llama-server reported 15,088 MiB of model buffers, 3,136 MiB of KV
cache, 150 MiB of recurrent state, and 495 MiB of compute buffers on the PRO
6000. Its host scope is capped at 8 GiB `MemoryHigh`, 12 GiB `MemoryMax`, and
eight CPU cores; the runner has an independent 2/4 GiB high/max cap and a
two-core CPU quota.

At launch, the primary process occupied approximately 34.9 GiB and the
reviewer projected 18.9 GiB, leaving more than 40 GiB of GPU memory free.
System available memory remained approximately 22.6 GiB, and the unrelated
non-experimental service remained alive and unchanged. Compute contention can
increase wall-clock time, so throughput from this attempt must not be treated
as a standalone performance benchmark. All request streams, raw responses,
parse failures, usage, timing, runtime properties, and final records remain in
the append-only ignored trace directory. No remaining-source review is
authorized until the six calibration reviews pass operator inspection.
