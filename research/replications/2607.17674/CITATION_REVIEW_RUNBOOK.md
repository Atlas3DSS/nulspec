# Citation-review execution runbook

This runbook executes the citation audit separately from the paper's primary
experiment. It has no authority to change primary metrics, publish, train from
the traces, or send email.

## Preconditions

- Use citation-audit evidence contract `2607.17674-citation-audit-v1.0.1` and
  trace-only harness amendment `2607.17674-citation-audit-harness-v1.0.3`.
- After the preserved zero-weight calibration failure, use prospective runtime
  amendment `2607.17674-citation-audit-runtime-v1.0.2` and pass
  `citation_audit_config.v1.0.2.json` explicitly.
- Use teacher hierarchy `2607.17674-citation-teachers-v1.0.3`.
- Require the exact registered GGUF basename and record its runtime SHA-256.
- Bind a natively built llama-server from commit
  `f53577432541bb9edc1588c4ef45c66bf07e4468`; the runner records its SHA-256,
  byte count, and version output.
- Expose the reviewer only on loopback. Never send acquired source text to a
  remote Qwen endpoint.
- Start only after the selected GPU is idle and the host retains safe RAM
  headroom. Do not stop or reconfigure unrelated services.
- The citation runner must acquire the same exclusive, nonblocking host lock as
  every primary arm before it inspects a route, writes a trace, or sends a
  request. Lock contention is a terminal preflight rejection, not a review
  attempt. Stop an already-started idle model server after such a rejection.
- Runtime schema preflight v1.0.1 must acquire that same lock and produce a
  fresh eligible pass before replacement calibration. The earlier concurrent
  parser check is retained as diagnostic-only evidence.

## 1. Start the local Qwen route

The exact operational flags are retained by llama-server's `/props` response in
the Qwen trace. The first attempt uses the registered 50,000-token context,
full GPU offload, flash attention, one slot, and f16 KV cache. A startup failure
has no scientific weight and must be logged before any parameter adjustment.
Starting the route does not reserve experimental authority; the citation
runner's v1.0.3 lock check remains mandatory and fail-closed.

```bash
CUDA_VISIBLE_DEVICES=0 llama-server \
  -m /path/to/Qwen3.6-27B-Heretic2-Uncensored-Finetune-Thinking.Q4_K_M.gguf \
  --alias qwen3.6-27b-citation-reviewer \
  -ngl 999 -fa on -c 50000 -np 1 -b 2048 -ub 512 \
  -ctk f16 -ctv f16 --threads 8 --threads-batch 8 \
  --metrics --host 127.0.0.1 --port 8080
```

## 2. Run the six-source calibration

Use a new append-only trace directory below the study's ignored `work/` tree.
The packet-builder attempt itself is immutable and validated before launch.

```bash
python scripts/run_2607_17674_qwen_citation_audit.py \
  --review-plan /path/to/review-plan.json \
  --packet-root /path/to/frozen-packet-root \
  --trace-root research/replications/2607.17674/work/citation-qwen/attempt-ID \
  --route workstation=http://127.0.0.1:8080 \
  --gguf-path /path/to/registered-reviewer.gguf \
  --llama-binary /path/to/pinned/llama-server \
  --config protocols/2607.17674/citation_audit_config.v1.0.2.json \
  --phase calibration
```

Do not begin the remaining 35 sources until every calibration chunk and all six
source syntheses are structurally valid and the human/Codex operator has read
the six final reviews for obvious grounding or calibration failures. Preserve
all invalid attempts and reasoning traces.

## 3. Complete Qwen review and build the bounded teacher packet

```bash
python scripts/run_2607_17674_qwen_citation_audit.py \
  [same bound arguments] --phase remaining

python scripts/build_2607_17674_citation_teacher_packet.py \
  --qwen-trace-root research/replications/2607.17674/work/citation-qwen/attempt-ID \
  --output research/replications/2607.17674/work/citation-teachers/attempt-ID/qwen-packet.json
```

## 4. Run independent teachers, Codex, and terminal validation

The GLM and Kimi runner refuses to start unless at least one registered
credential route exists for each logical teacher. Secrets are never serialized.
Calls are concurrent and independent; every stream, response, reasoning trace,
failure, usage record, and cost is append-only. Missing cost blocks repair.

```bash
python scripts/run_2607_17674_citation_teachers.py \
  --teacher-packet /path/to/qwen-packet.json \
  --trace-root research/replications/2607.17674/work/citation-teachers/attempt-ID

python scripts/run_2607_17674_codex_citation_adjudication.py \
  --teacher-packet /path/to/qwen-packet.json \
  --teacher-trace-root research/replications/2607.17674/work/citation-teachers/attempt-ID

python scripts/validate_2607_17674_citation_teacher_trace.py \
  --teacher-packet /path/to/qwen-packet.json \
  --teacher-trace-root research/replications/2607.17674/work/citation-teachers/attempt-ID \
  --output research/replications/2607.17674/work/citation-teachers/attempt-ID/validation.json
```

Only after terminal validation may a separately sanitized packet be prepared
for the one-shot final Fable release critique. Fable is not part of this
recurring teacher loop, and no resubmission is allowed. Publication and every
author-email draft remain subject to their independent human approval gates.
