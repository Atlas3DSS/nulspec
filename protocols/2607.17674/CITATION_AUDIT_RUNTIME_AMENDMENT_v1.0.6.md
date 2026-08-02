# Citation-audit runtime amendment v1.0.6

The eligible v1.0.5 calibration completed all six preregistered sources and
passed its bounded outer gate. Its remaining phase also resolved the exact
v1.0.4 output-budget blocker: the first Bowman et al. evidence chunk reached a
normal stop after 8,397 completion tokens, 205 beyond the old ceiling, and
passed validation on its first attempt. The next Bowman chunk repaired five
ungrounded excerpts within the registered two-attempt limit and produced a
valid source synthesis.

The v1.0.5 pass later failed closed on the second Gu et al. evidence chunk.
Both permitted calls reached normal stops. Attempt one contained one excerpt
that was not a substring of any physical extraction line on its cited page.
The generic repair then joined three adjacent PDF lines into another excerpt,
despite the frozen exact-line instruction, and exhausted the second attempt.
There was no output truncation, context overflow, transport failure, OOM, or
accepted Gu record. No remaining-phase completion, teacher packet, external-
teacher request, or full-audit completion exists.

The terminal v1.0.5 trace contains 594 files and 110,739,555 bytes. Its
record-stream SHA-256 is
`95835a3acb2ab541284bc7369e6cc43a9b0fbc17f8efff0f277dd8f6885014bf`;
the separate index SHA-256 is
`f7432c8f4fc4e1b9971c9f41635150bfa091d019e2d88104236702ac132af3e8`.
The accounting record has SHA-256
`5c31970dd90fee0043a2d402785127b67bf1748adb235f1da3bed9e2c1020569`
and reports 52 completed local calls: 43 valid attempts and nine retained
invalid attempts, 599,197 prompt tokens, 256,425 completion tokens, 855,622
total tokens, and 6,285.541703 seconds of accelerator request wall-clock.
Provider charge was exactly $0; electricity and hardware cost remain
unmeasured. The server was stopped after failure before its final cgroup event
file was copied, so exact post-calibration cgroup counters are unavailable;
continuous guard telemetry showed no host-memory or temperature stop.

Runtime v1.0.6 makes two prospective structural-repair changes:

1. After an evidence call fails validation, its next model request appends the
   hash-bound conservative exact-line repair policy in
   `prompts/citation_repair_runtime_v1.0.6.txt`. It instructs the reviewer to
   delete a failing candidate or replace it with a short substring copied from
   exactly one source line, never to join or reconstruct lines, and to prefer an
   empty chunk-level evidence list when no exact line is suitable. Initial
   evidence requests and all synthesis requests retain their prior prompts.
2. Evidence calls receive at most three structural attempts rather than two.
   Synthesis calls remain capped at two. Every invalid attempt remains immutable
   and has zero evidentiary weight.

The Qwen GGUF, llama.cpp revision, context, offload, KV precision, thinking
mode, seed, temperature, top-p, top-k, output ceilings, immutable packets,
chunking, initial evidence prompt, synthesis prompt, schemas, transport grammar,
client-side grounding validator, source order, calibration set, and outer gate
are unchanged. No v1.0.5 output is copied into a v1.0.6 trace.

The amended settings are immutable in
`citation_audit_config.v1.0.6.json`. Before one fresh calibration, the config,
repair prompt, amendment, and runner bindings must be committed and tagged,
focused tests and static checks must pass, and a fresh lock-held runtime
preflight must succeed. Remaining review stays blocked until all six new
calibration sources pass the unchanged outer gate.
