# RTX PRO 6000 route smoke test

Date: 2026-07-30 (America/Los_Angeles)

The former mixed-GPU launcher used CUDA ordinal selection and the shared
llama.cpp binary had only `sm_86`/`sm_89` kernels. It could enumerate the RTX
PRO 6000 Blackwell card, then failed on the first CUDA operation with:

```text
no kernel image is available for execution on the device
```

The new route:

- selects `GPU-d739b9c5-bfbb-e95a-bbf1-7122f38c2cf1` by UUID;
- verifies the product name contains `RTX PRO 6000`;
- uses `build-cuda-pro6000/bin/llama-server`, built with CUDA 13.1 for
  `sm_120a`;
- serves the existing Qwen3.6 27B GGUF on port 8081;
- defaults to 8 CPU threads plus nice/ionice and a 10 GiB free-RAM guard.

Observed end-to-end test:

- `/health`: ready
- `/v1/models`: model listed
- `/v1/chat/completions`: valid response
- measured generation: approximately 75.95 tokens/s
- server stopped normally after the request
- GPU allocation returned to approximately 20 MiB
- unrelated services remained healthy and outside the experimental cgroup

The test did not signal, restart, reconfigure, or place unrelated services in
the experimental cgroup.
