# Citation-runtime preflight amendment v1.0.1

The first exact-runtime schema preflight ran concurrently with an active
primary factorization arm. It issued only two one-token diagnostic requests and
cannot count as a citation review, but it still used the same host and GPU
without acquiring the repository's experiment lock. Its complete trace remains
immutable and its narrow parser-compatibility observation remains diagnostic
only. It is not an eligible reference execution under the host resource
policy.

This prospective amendment is frozen before an eligible runtime preflight or a
replacement citation calibration. The preflight now acquires the same
exclusive, nonblocking `nulspec-experiment.lock` as primary arms and the Qwen
citation runner. Acquisition occurs before route inspection, trace creation,
or a model request. Contention exits without creating a trace. The open handle
is retained throughout both schema requests and its held state and mechanism
are recorded in preflight input and completion records.

An uncontended fresh preflight on the exact pinned server, model, and runtime
must pass before replacement calibration. This does not change the v1.0.2
transport schemas, generation settings, canonical client-side validation, or
scientific protocol. The amended preflight is frozen by tag
`2607.17674-citation-runtime-preflight-v1.0.1`.
