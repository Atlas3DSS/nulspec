# Citation-audit runtime amendment v1.0.8

Runtime v1.0.7 completed its fresh six-source calibration, passed the registered
exact-replay outer gate, and produced 35 valid final source reviews. It stopped
at the Yakowitz and Spragins synthesis after two structurally invalid attempts.
Both attempts populated `evidence` with a paraphrased chunk summary even though
the validated evidence record explicitly contained no evidence candidates. The
review contract correctly rejected both with `evidence[...] was not copied from
chunk evidence`. They retain zero evidentiary weight. This is a local reviewer-
harness limitation, not an error in the cited source or target paper.

The failed v1.0.7 boundary is sealed as 1,877 files and 363,164,131 bytes in
`v107-tail-failure.file-manifest.json`, whose SHA-256 is
`4979458f79c87f77a891d31134e22409c76ab20110db7cca901c2acda75dc91d`.
The run input, terminal event stream, and already passed outer gate have SHA-256
values
`e9a51ba113f7f433ba770e0d00e861feb4bc0d7aff618c4456e723b859d7d2d3`,
`b873f70a5886ef51ce9f291746cf58bd0002c4c012737e1b43d7f26364d1a906`,
and
`c7455705868d4d1d7f03aa60a9f9b929d275c653162682a2c482041d76a364dc`.
The prior trace is never resumed or edited.

Runtime v1.0.8 is a versioned six-source continuation, not a claim that all 41
sources were generated under one runtime. Its committed continuation manifest
binds the complete prior tree, parent input and events, outer gate, exact 35/6
population split, and pending citation keys. Before accepting the prior 35, the
continuation rehashes every sealed file and revalidates every final review
against its immutable source plan, validated evidence records, accepted parsed
object, and valid attempt record. It copies no prior model output into the new
trace. Logical completion records the source trace and final-review hash for all
41 sources so a separately versioned teacher projection can reconstruct both
provenances without mutating either trace.

The first Yakowitz synthesis request remains unchanged. Only after a synthesis
attempt fails structural validation, a frozen conservative repair suffix says
that `evidence` may contain only exact objects from the same occurrence's
validated `evidence_candidates`; when none exist, the array must be empty and
the limitation must be disclosed. The synthesis attempt ceiling increases from
two to three. Evidence review already retains its separately registered three-
attempt ceiling and exact-line repair policy.

Every evidence or synthesis attempt, including a repair, is rendered and
tokenized by the same local llama.cpp route before generation. The request
proceeds only when its
exact prompt plus the full registered output reservation fits both the 50,000-
token registered minimum and the live server context. This gate is recorded in
the attempt and has no citation-decision weight.

The Qwen GGUF and llama.cpp bytes, context, full GPU offload, f16 KV precision,
thinking mode, seed, temperature, top-p, top-k, output ceilings, packets,
schemas, source order, evidence and initial synthesis prompts, validators, and
outer-gate decision are unchanged. The remaining six sources rerun from their
immutable packets. The 35 carried reviews keep their original v1.0.7 runtime
provenance. Invalid attempts remain visible with zero weight.

GLM, Kimi, Codex adjudication, Fable, publication, training use, and email stay
blocked until the logical 41-source Qwen completion validates. The continuation
config, manifest, prompt, runner, preflight, tests, and this amendment must be
committed and tagged before a live request. A fresh exact-
runtime grammar preflight, context audit including the repair suffix, exclusive
experiment lock, and protected-workload capacity check are required.
