# Citation-audit runtime amendment v1.0.7

Runtime v1.0.6 completed its fresh six-source calibration, passed the bounded
outer gate, and completed six additional source reviews. It was then stopped by
the operator during the second Galichin et al. evidence chunk after an unrelated
interactive Windows workload began actively sharing the workstation RTX 4090. The first
interrupted call retained 5,371 streamed events but no terminal response or
usage record. An exact-identity diagnostic resume received no model event before
the operator stopped it. Neither incomplete call has evidentiary weight, and the
stop is a local operational failure rather than a Qwen citation judgment or an
upstream-paper limitation.

The sealed v1.0.6 trace contains 544 files and 106,079,040 bytes. Its record-
stream SHA-256 is
`bd6ab7c8303954301b3ac91f3d8272398eb98f728ce36b4a31cca87124b6bc05`;
the separate index SHA-256 is
`279548c08b20f9e0f2266d4b4511d21c04d488cea71a26af2cb22deb145ec3c9`.
The completed-attempt accounting record has SHA-256
`a3141efd6b9b265cc94c277ad60d30cac895d996c629235a09d0a8f9e15b421f`
and reports 46 completed local calls: 39 valid attempts and seven retained
invalid attempts, 501,199 prompt tokens, 241,318 completion tokens, 742,517
total tokens, and 5,992.068087 seconds of accelerator request wall-clock. The
two incomplete calls add a separately bounded 734.054536 seconds but lack
terminal provider usage records, so they are disclosed outside the standard
accounting rather than estimated as token totals. Provider charge was exactly
$0; electricity and hardware cost remain unmeasured.

The safe restart exposed a harness error. llama.cpp returns a process-random
`props.media_marker` used for multimodal placeholders even when the loaded model
is text-only. v1.0.6 copied the full `/props` response into its stable run input,
so a scientifically identical server restart failed equality before appending
an event or making a model request. Pinning `LLAMA_MEDIA_MARKER` to the original
value proved that this nonce was the sole identity difference. The immutable
v1.0.6 run input was never edited.

Runtime v1.0.7 makes two prospective trace-lifecycle changes:

1. Resume equality removes exactly `props.media_marker` from both sides of the
   comparison. The raw value remains in the initial run input, and every resume
   records the newly observed excluded value. Any other route, model, context,
   build, prompt, schema, binary, host, or config difference still fails closed.
2. A process resuming an unmatched phase emits `qwen_phase_resumed` rather than
   a second `qwen_phase_started` event. Completed-attempt accelerator time
   remains the authoritative compute measure; phase wall-clock may include an
   offline gap after an unclean interruption and must be labeled accordingly.
3. The immutable run input binds the exact citation runner, review-contract
   validator, and packet-validator source files by workspace-relative path,
   byte count, and SHA-256. A code change can no longer resume the same trace.

The Qwen GGUF, llama.cpp revision, context, full GPU offload, f16 KV precision,
thinking mode, seed, sampling parameters, output ceilings, immutable packets,
chunking, prompts, schemas, validation, source order, calibration set, and outer
gate are unchanged. No v1.0.6 model output is copied into a v1.0.7 trace.

The amended settings are immutable in `citation_audit_config.v1.0.7.json`.
Before one fresh calibration, the config, amendment, runner, preflight, tests,
and documentation must be committed and tagged; focused tests, static checks,
and a fresh lock-held runtime preflight must pass. Remaining review stays
blocked until all six fresh calibration sources pass the unchanged outer gate.
