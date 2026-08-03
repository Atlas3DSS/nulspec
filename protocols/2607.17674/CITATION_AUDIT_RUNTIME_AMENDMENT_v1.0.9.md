# Citation-audit runtime amendment v1.0.9

Runtime v1.0.8 was a fresh, versioned attempt to complete the exact six-source
tail left by the sealed v1.0.7 parent. It produced valid final reviews for the
first three sources, then failed closed on the first evidence chunk for
`zhang2024graphInducedVae`. Attempt 1 used the full 12,288-token completion
allowance in reasoning and returned no final object. Attempts 2 and 3 returned
otherwise structurally valid objects, but the immutable client validator found
two and one page-ungrounded excerpt candidates respectively. All three attempts
retain zero weight. This is a local-reviewer/harness limitation, not an error in
the cited source or target paper.

The stopped v1.0.8 trace is preserved as 218 files and 38,189,877 bytes in
`v108-grounding-exhaustion.file-manifest.json`, whose SHA-256 is
`420db6b750194fb2d40e8312cf0226625441d4b28bbd0f06d0161f78e0451f3b`.
Its run input and terminal event stream have SHA-256 values
`d11d1b54ecb84c0bc044440d43fca12929e9668a8014f5191762b2b8fa6ffd32`
and
`2221d0d5920702e96f6384af4b8c07a245f278e3cb1d39ea6428f2bdfb2cc1f1`.
That trace is never resumed, edited, or promoted to logical completion.

Runtime v1.0.9 reruns all six pending sources from their immutable packets. It
retains v1.0.8's prompts, model, generation settings, schemas, three-attempt
ceilings, context gate, sealed-v1.0.7 lineage checks, and synthesis repair. It
adds one narrow non-generative evidence repair. When, and only when, a parsed
evidence object passes every frozen contract check except exact page grounding,
the client deletes each rejected candidate. If a finding becomes empty and its
model-supplied empty-evidence explanation was blank, the client inserts the
fixed administrative sentence registered in the config. It then reruns the
complete unchanged evidence validator. Mixed structural errors, transport
failures, malformed objects, wrong occurrence identities, and any object that
still fails validation receive no deterministic repair.

Every repaired attempt preserves the exact original model object, the repaired
object, both object hashes, every initial validator error, and for each deletion
the occurrence, original index, page, candidate hash, and excerpt hash. The
repair changes no claim focus, summary, relevance statement, stance, source
identity observation, retained candidate, or citation verdict. Synthesis sees
only the resulting client-grounded candidate set. This policy is conservative:
it can remove purported support but cannot manufacture support.

The prior 35 final reviews remain bound to runtime v1.0.7. The v1.0.9 logical
completion must bind exactly 35 v1.0.7 plus six v1.0.9 final reviews. GLM, Kimi,
Codex adjudication, Fable, publication, training use, and email remain blocked
until that 41-source completion and the separately versioned teacher projection
validate.

The v1.0.9 config, continuation manifest, runner, preflight, tests, and this
amendment must be committed and tagged before any live v1.0.9 request. A fresh
exact-runtime grammar preflight, context audit, exclusive experiment lock, and
protected-workload capacity check remain required.
