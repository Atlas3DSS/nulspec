# Citation-audit harness amendment v1.0.4

Runtime v1.0.5 was committed and tagged after its output-ceiling change passed
focused tests and static validation. The first eligible calibration command was
then rejected before trace creation, lock acquisition, route inspection, or a
model request because the runner's separate runtime-identity allowlist still
ended at v1.0.4. The runtime-amendment binding map already contained v1.0.5;
the duplicated allowlist did not.

Harness v1.0.4 derives the supported runtime-version set from the existing
runtime-amendment map plus the original v1.0.1 contract. A focused assertion
requires the exact set `{1.0.1, 1.0.2, 1.0.3, 1.0.4, 1.0.5}`. This removes the
duplicated registration point that caused the pre-execution rejection.

No source packet, prompt, schema, validator, grounding rule, model, llama.cpp
binary, context setting, decoding setting, retry rule, calibration gate,
accepted output, or scientific decision changes. A fresh invocation ID and
new trace root are required after this amendment is committed, tagged,
synchronized, and tested.
