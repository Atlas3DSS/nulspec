# Citation-audit runtime amendment v1.0.5

The eligible v1.0.4 calibration completed all six preregistered sources and
passed its bounded outer gate. The authorized remaining phase then failed
closed on the first evidence chunk of Bowman et al. Both permitted calls ended
with llama.cpp `finish_reason: length` at exactly 8,192 completion tokens. The
first left a truncated JSON object; the structural-repair call spent the full
allowance in retained reasoning and returned no final content. The complete
v1.0.4 trace is immutable, terminally failed, and supplies no remaining-source
citation decision or teacher input.

Runtime v1.0.5 makes one prospective transport-budget change:

1. Evidence calls receive a maximum of 12,288 completion tokens rather than
   8,192. This is a ceiling, not a required generation length; a normal stop
   remains authoritative.

The synthesis ceiling remains 12,288 tokens. The registered Qwen GGUF,
llama.cpp revision, 50,000-token minimum context, full GPU offload, f16 KV
cache, thinking mode, seed, temperature, top-p, top-k, prompt text, exact-line
presentation, immutable source packets, chunking, schemas, transport grammar,
client-side grounding, source order, calibration set, and two-attempt repair
limit are unchanged. No accepted v1.0.4 output is copied into a v1.0.5 trace.

The amended settings are immutable in
`citation_audit_config.v1.0.5.json`. Before one fresh calibration, the new
config and code bindings must be committed and tagged, every focused test must
pass, the largest exact request must retain context headroom for the expanded
ceiling, and a fresh lock-held runtime preflight must succeed. The previously
measured largest rendered request contains 35,644 tokens, so the new ceiling
totals 47,932 and leaves 2,068 tokens even against the registered 50,000-token
minimum. Remaining-source review stays blocked until all six new calibration
sources pass the unchanged outer gate.
