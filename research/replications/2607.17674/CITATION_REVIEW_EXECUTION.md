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

### Terminal calibration outcome

This attempt did not produce a valid calibration review and has no citation
evidentiary weight. The pinned server rejected the nested bounded JSON Schema
grammar before both requests. Each request then used all 2,048 allowed output
tokens as reasoning (`finish_reason = length`) and returned no final content;
the fail-closed client rejected both with `Qwen returned no final content`.
The second invalid response completed at `2026-08-02T06:21:16Z`, after which
the operator stopped calibration before another source and later stopped the
idle reviewer scope.

The complete failed trace was copied back without deletion after server
shutdown. Source and destination path/size inventories both hash to
`e85e966503206806ff092269781e09d67f633d56d7027ad6627ae86fc5022227`.
It includes both requests, response schemas, raw SSE streams, normalized
events, assembled reasoning, usage, timing, attempt records, server log, and
runtime input. A new attempt requires a prospective trace-only amendment and
an exact-runtime grammar/output-budget regression test; this directory will
not be resumed or overwritten.

## Runtime-v1.0.2 schema preflight

The prospective runtime amendment was exercised at
`2026-08-02T07:56:28Z` against the same pinned llama-server executable, model,
hardware, context size, GPU-offload, attention, KV-cache, batching, thread, and
host-scope settings. The preflight implementation is bound to repository
commit `7a1ffac278c694bb8443b6918e665fa5bbf84230`. It submitted the exact
transport schema derived for each of the evidence and synthesis stages, with a
one-token output ceiling so the test measured grammar construction rather than
review quality.

Both requests returned HTTP 200. The server-log slice contained none of the
registered grammar-failure markers, including the bounded-repetition failure
that terminated the original calibration. The evidence and synthesis
transport-schema hashes are respectively
`7386b7c08b6b83c93afcb7fd4dfa0eac170cb66426867bbecb554ee82a301870`
and
`090a3a6928393624cf71563654e79f0284d1294b64b47653d6263251170649b1`.
The preflight ran concurrently with the active primary factorization arm and
did not acquire the host experiment lock. This is a process deviation even
though the requests were limited to parser compatibility. The result is
therefore diagnostic only: it does not count as an eligible reference
execution or citation review, and it does not show that the expanded output
budgets are sufficient. Prospective preflight v1.0.1 applies the same
fail-closed host lock as the primary and citation runners; an uncontended fresh
preflight is required before replacement calibration.

After server shutdown, the complete preflight trace was copied back without
deletion. Source and destination path/size inventories both hash to
`836ee6bee9e7be996e4aefd5e49e46d257f361211ec69bc54ac72ecc147b0507`.
The trace includes the server log, canonical and transport schemas, requests,
raw SSE streams, normalized events, assembled responses, route metadata, and
the machine-readable completion record. A new scientific calibration attempt
must use a fresh trace directory, the v1.0.2 runtime contract, and an eligible
uncontended schema preflight.

## Eligible workstation runtime and preflight

The registered 16,547,400,352-byte GGUF was copied to the idle workstation and
independently matched SHA-256
`b62cbed05de4b9e368a19cf0dd575a43bedd0546920a6e31a812e34ff67299e9`.
The first copied llama-server executable could not start because a build from
the newer dev-box OS required glibc and libstdc++ symbol versions unavailable
on the workstation. No model load, route, trace, or request occurred; this is
our staging error `LRS-LOCAL-062`.

We then built the same pinned llama.cpp commit
`f53577432541bb9edc1588c4ef45c66bf07e4468` natively for compute capability
8.9. The release build used CUDA 12.8, GCC 11.4, CMake 4.4, full-attention
quantization kernels, CUDA graphs, native CPU instructions, and explicit build
number 8942. The resulting 9,201,200-byte `llama-server` reports version
`8942 (f535774)` and has SHA-256
`536f89a58f1e5e27bbe35d12965ae9d741ea121aa4e1b6b3dfcf84f1f7464350`.

The replacement route is loopback-only and retains the registered 50,000-token
context, full GPU offload, flash attention, one slot, f16 KV cache, batch 2,048,
microbatch 512, and eight inference threads. The server projected 18,868 MiB of
device memory, left 3,969 MiB free at launch, and offloaded all 65 layers. Its
host scope retains the 8/12 GiB high/max memory limits and eight-core CPU cap.

The fresh runtime-v1.0.2 preflight completed at
`2026-08-02T08:59:30.383200Z` while holding the shared exclusive workstation
experiment lock. Both exact transport schemas returned HTTP 200, their hashes
matched the earlier diagnostic, and the server-log slice contained no grammar
failure marker. The completion-record SHA-256 is
`ee5aaa8a6fa5b86ac7a4497ad27af0a7272550ff147c1d74b8c6f5c8c5756af7`.
An 18-file, 45,476-byte preflight inventory has SHA-256
`c0bedf739a7ac5f61bb91bdb9e1cea6cecb4e335e2188173d89137a16086cd5a`.
This is the first eligible runtime preflight and authorizes a fresh calibration
attempt, but is not itself citation evidence.

The first calibration command after preflight supplied one directory level too
deep for `--packet-root` and failed validation before lock acquisition, trace
creation, or request. It is retained as our error `LRS-LOCAL-063`. A new
invocation using the immutable packet-attempt parent acquired the lock, bound
run-input SHA-256
`236ec7344f944a4fdc92d7882e2c2e019b87821f9f282f8a00df3fffcf9a1449`,
and began the six-source calibration at `2026-08-02T09:00:57.893713Z`.

### Terminal workstation calibration outcome

The eligible v1.0.2 calibration terminated at
`2026-08-02T09:04:55.282749Z` without completing the first evidence chunk. Both
allowed generations returned structurally valid JSON, but the unchanged exact
grounding validator rejected their excerpt/page pairs. Attempt 1 had three
invalid candidates; attempt 2 received those errors as repair context and
returned five invalid candidates. Their attempt-record SHA-256 values are
`66e28450f7ce488e421c24bfb45048c92703c72eaef0d6cc5fe892397cea04cb`
and
`c21e9b299925bb72ea100ecf665316f35cb4b2554f8d46aa95f221766b0d1f0d`.
No `accepted.json`, source synthesis, calibration completion, final review, or
teacher input exists. This attempt has zero citation evidentiary weight.

Manual outer-loop inspection found that the validator behaved as registered.
The reviewer silently removed line-wrap hyphens from several extracted-PDF
quotes and inferred page numbers from section position or printed headers
instead of locating the quote within the supplied character spans. One attempt-1
candidate that preserved both the exact substring and correct page passed, while
the altered or mislocated candidates failed. This supports a reviewer-input
usability diagnosis rather than weakening the grounding rule.

The complete 23-file, 4,348,519-byte attempt inventory has SHA-256
`3b917c90f8659dc911cb595f8037e0a431e1d86e034e078735184049787b6831`;
the event log has SHA-256
`366d4fac5f312d8a0c23c98cecce9a8d9346ccc500ddfa08ad79f228d0b7efd5`.
Runtime v1.0.3 is a prospective presentation-only amendment: it gives Qwen an
exact page-labeled view derived from the same immutable packet and explicitly
forbids silent dehyphenation. The raw packet, schemas, validator, model,
generation settings, retry count, and calibration gate remain unchanged.

### Prospective v1.0.3 verification

Before freezing v1.0.3, all 112 frozen evidence packets passed the new
lossless-presentation coverage check. The two runtime-focused test files passed
16/16 tests; scoped Ruff `E`, `F`, and `I` lint, Ruff formatting, JSON parsing,
repository hygiene, whitespace checks, and the frozen protocol check all
passed. The repository-wide suite passed 161 tests and reached only the known
cross-study missing-fixture failure recorded in LRS-LOCAL-059. No Qwen request
or research artifact used the amendment before these checks.

### Eligible v1.0.3 preflight

At `2026-08-02T09:26:50.632134Z`, the tagged v1.0.3 runtime completed a fresh
uncontended preflight while holding the shared workstation experiment lock.
Both exact transport schemas returned HTTP 200, retained their registered
hashes, and produced no grammar-failure marker in the bound server-log slice.
The configuration SHA-256 is
`525344271f056a719b16481f9e8d1f77ff619476d98034016c05e083e9383f24`;
the completion-record SHA-256 is
`985fbb01752d234b32b79386cef33cba1a6d4f380f1f0e4a85b276c63d722f25`.
The complete 18-file, 46,413-byte preflight inventory has SHA-256
`bcf02f458addddf65c4e8d987439a6b904b6241cbcc4179cd590b6b78257a25e`.
This preflight authorizes one fresh v1.0.3 calibration attempt; it is not
citation evidence.

### Terminal v1.0.3 calibration outcome

The fresh v1.0.3 calibration ran from `2026-08-02T09:28:06.076138Z` through
`2026-08-02T09:31:36.644255Z` and again failed closed on the first Allman et
al. evidence chunk. Both allowed calls returned structurally valid JSON. The
first had two invalid excerpt/page pairs, and the repair attempt also had two.
No `accepted.json`, synthesis, calibration completion, final review, or teacher
input exists; the trace has zero citation evidentiary weight.

Outer-loop comparison against the exact page-labeled request showed that page
selection was now correct and several candidates grounded successfully. Every
remaining failure instead joined words across physical PDF line-wrap hyphens:
for example, the acquired page contains `statistical ap-` followed by
`plications`, while Qwen returned `statistical applications`. It similarly
rewrote `parame-`/`ters`, `argu-`/`ments`, and symbolic/spacing details in a
Kruskal-rank excerpt. The unchanged validator therefore behaved correctly.
The page-level amendment improved locator behavior but did not make this model
reliably copy exact multi-line PDF text.

The two attempt-record SHA-256 values are
`b5924f57048b350540d067a07df22da852436e56271ce7aee0b9b90dbd1fc513`
and
`21ee19d552154ef75fd3b0cf23e78c622d3ee4692a4bf99aaff677b94dea3b82`.
The complete 23-file, 3,877,527-byte trace inventory has SHA-256
`2c979b4f53c31b79629d34f4b98e8f61b92a9436c84aaf6af1de597f0e4ed9d9`;
the event log has SHA-256
`dea07da10acadd305b3f13e786b57430ac6eb173ea93a8f67464d03d31f1b4ce`.
A further attempt requires a new prospective contract that constrains excerpts
to exact physical source lines; retrying v1.0.3 is not authorized.

A separate ignored outer-loop label record scores the eligible v1.0.2 and
v1.0.3 failed calibration traces at 4/10 and 5/10 respectively under the frozen
Qwen reviewer-quality rubric. It binds every attempt-record and trace-manifest
hash, records valid/invalid candidate counts and error classes, and supplies
four exact page-grounded correction examples for future supervised curation.
Its SHA-256 is
`e5f45c0c89f9428bd64492d27da772f96e8c311785562fe6537fcdbc39bae915`.
The label explicitly carries zero citation-decision weight and authorizes no
automatic training, publication, teacher input, email, or release action.

### Prospective v1.0.4 verification

The first line-level draft represented every physical line as an object with a
line number and SHA-256. The required pre-execution context audit rejected that
design: across the 112 frozen evidence packets, median prompt text was 52,877
tokens and the maximum was 99,609 before reserving any output. No review request
used that draft. LRS-LOCAL-072 records the contained design error.

The corrected v1.0.4 presentation uses an ordered array of exact line strings,
with one-based array position as the line number and the existing page SHA-256
as the integrity binding. All 42,693 physical line entries across all 112 packets
reconstructed their exact pages and preserved full packet coverage. While
holding the exclusive experiment lock, the registered `b8942-f535774` runtime
rendered each complete chat through `/apply-template` and tokenized it through
`/tokenize`. Exact rendered prompts ranged from 1,866 to 35,644 tokens with a
median of 14,394. The largest packet was
`yao2023treeOfThoughts:chunk-0001`; after reserving all 8,192 evidence-output
tokens, its total was 43,836, below the live 50,176-token context. The largest
rendered prompt has SHA-256
`252edf300a3aca64c9673c366cee9476abcd8201076a866f5990beeeea3a4969`.

The prospective configuration SHA-256 is
`99f4d557a6df2523f9b8149c2017ab071cfe2afd51fa67d2c24fdf546cb5007f`.
The supplemental and effective evidence-prompt SHA-256 values are respectively
`08e985e57d86270ad46fe5475ef96580bc8a5257144d1768e665099cd311baab`
and
`ef73a07fe1c7492fe38ad21679eb5becb9b45615503e7447bcfac40b1fcc6046`.
The two runtime-focused files passed 19/19 tests; scoped Ruff lint, Ruff
formatting, JSON parsing, Python compilation, repository hygiene, whitespace,
and the frozen protocol check passed. The repository-wide suite passed 164
tests and reached only the known unrelated missing fixture recorded in
LRS-LOCAL-059. No v1.0.4 model generation is authorized until the amendment is
committed, tagged, synchronized, and passes a fresh lock-held preflight.

### Eligible v1.0.4 preflight

At `2026-08-02T09:55:09.686981Z`, tagged v1.0.4 completed a fresh uncontended
preflight while holding the shared workstation experiment lock. Both exact
transport schemas returned HTTP 200 and the bound server-log slice contained
no grammar-failure marker. The completion-record SHA-256 is
`451e91761d68419a240dda402403b20a137c2804a1fd312503f9adfe6fd65e8c`.
The complete 18-file, 46,533-byte preflight inventory has SHA-256
`cfc247e2eccadbecabe3e3eadb6e34c846fc92cff5822eee2ff517023d816184`.
This preflight authorizes one fresh v1.0.4 calibration and is not citation
evidence.

### Terminal v1.0.4 calibration outcome

The eligible v1.0.4 calibration ran from `2026-08-02T09:55:52.064754Z`
through `2026-08-02T10:07:43.991579Z` and failed before completing the first
source. The first Allman evidence chunk used both registered attempts: attempt
1 exhausted its 8,192-token output allowance and ended with incomplete JSON;
attempt 2 was structurally valid and exactly grounded. The second chunk was
valid on its first attempt. Neither request for the third chunk emitted a
single response byte before its 120-second first-event deadline. No third-chunk
record, source synthesis, calibration completion, final review, or teacher
input exists. The partial records therefore have zero citation-decision weight.

This was our execution failure, not a paper, source, or demonstrated Qwen
scientific failure. The reviewer scope had an 8 GiB `MemoryHigh`, 12 GiB
`MemoryMax`, and 2 GiB swap maximum. At terminal diagnosis it had crossed the
high threshold 105,483 times, reached the swap limit, accumulated severe full
memory pressure, and was sleeping in `mem_cgroup_handle_over_high`; it recorded
no max-limit, OOM, or OOM-kill event. The process became responsive immediately
after a post-terminal high-limit increase and then stopped cleanly. Its
89,923-byte append-only server log has SHA-256
`5237b14b5f6a6bfbd9ae78131566e60a10c519ffef429efd3fff09e74f48b486`.

The immutable 50-file, 8,279,287-byte trace has content-index SHA-256
`cb9ff04296f31591e691eb170f82f48887a91805826eddff7461870b0f2e0983`.
That index hashes bytewise path-sorted records containing each relative path,
byte count, and file SHA-256. The event-log SHA-256 is
`4afe7c87943bcc74b771af02cc57db3c3e3f9d8dfafd681c30e383c3aadfbd08`.
The separately stored machine-readable index has SHA-256
`7929d7e3b5d3bc9632e1296662e02b142637904e8071a82b89575ab8271354dd`.
A separate ignored Codex label scores the available Qwen output 5/10, separates
the two no-output infrastructure failures from reviewer quality, and records
two evidence-selection corrections. Its SHA-256 is
`0bbb990f2a0e160513a8590a10343b472fb23fc7eda9f9a4f4178be71f05fd9c`.
It authorizes no citation decision, teacher input, training projection,
publication, or email.

The linked private cost record has SHA-256
`0ede82c8f247bbdbd40dcfec408d623a95a1ce55754023c496b228c33ef0f33e`.
It records 62,278 prompt tokens, 18,814 completion tokens, three completed
responses, two no-response attempts, and 711.926825 seconds of accelerator
wall-clock. External-provider cost was exactly $0; electricity and hardware
capital cost were not measured and are not estimated post hoc.

### Prospective host-envelope repair and replacement preflight

The replacement uses the identical v1.0.4 code, packet, prompt, schemas,
validator, GGUF, llama.cpp executable, model flags, sampling parameters,
attempt budget, and calibration order. Only the local server cgroup envelope
changed. The first proposed 12/16 GiB high/max repair was rejected before any
citation-bearing request: after model load and a one-token diagnostic schema
preflight, `MemoryCurrent` was within 81,920 bytes of `MemoryHigh` and the new
scope had already recorded 50,712 high-limit events. That diagnostic preflight
remains preserved with zero evidentiary weight.

Before replacement calibration, the preflight server envelope was set to 20 GiB
`MemoryHigh`, 24 GiB `MemoryMax`, and 4 GiB swap maximum. This remains below
half of the workstation's 94 GiB physical memory, whose available memory was
90 GiB at the correction point. The new server writes an append-only log and
retains the same eight-core quota, nice level, I/O priority, loopback route,
and one-slot GPU configuration.

With the final envelope active, a new exclusive-lock preflight completed at
`2026-08-02T10:14:44.129435Z`. Both exact transport schemas returned HTTP 200,
and the server-log slice contained no grammar-failure marker. The completion
record and server-log-slice SHA-256 values are respectively
`08a071f0bbea2af000e8acaeb6d7d8b7fdc901d9738f173aa5aa6317591e6300`
and
`594de1638bc66263d1b5bbb82bfdd6a8fc0568b14d9018bd0bb4b945e03344dd`.
The complete 18-file, 45,812-byte preflight has content-index SHA-256
`be94632678359010cb6f6f3672fe98c8f227bf58ef5036a1c2c2efc1e207c4af`.
This final preflight authorizes one fresh replacement v1.0.4 calibration and is
not citation evidence.

The replacement acquired the exclusive experiment lock and began at
`2026-08-02T10:15:07.348463Z`, with run-input SHA-256
`d7d8f7f97a23d0b8bc080d850eca2a3f76c331207cf7e7c981e59ea5b6d5e011`.
After its first evidence chunk and before any new high-limit event, the server
used 16,383,631,360 bytes while the advertised 8 GiB prompt cache was still
accumulating prompts. At `2026-08-02T10:22:16Z`, the host high/max limits were
therefore relaxed to 32/40 GiB while retaining the 4 GiB swap and eight-core
limits. The 40 GiB hard limit remains below half of physical workstation
memory. No request was canceled or restarted, and no model, route, packet,
prompt, schema, validator, generation parameter, or accepted output changed.
The append-only resource amendment and cgroup counters are retained with the
private server trace.
