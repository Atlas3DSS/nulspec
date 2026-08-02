# Error and limitation ledger

This ledger keeps our operational errors separate from upstream/release
limitations. Entries are never removed after correction.

## Our operational errors

### LRS-LOCAL-001 — malformed GitHub API metadata query

- **State:** corrected; no scientific effect
- **Observation:** the first commit-metadata command combined `gh api` pagination
  with a form field and then passed an unexpected response shape to `jq`.
- **Disposition:** reran a quoted GET URL with `?per_page=1`; no remote or local
  state was changed by the failed command.

### LRS-LOCAL-002 — incorrect small-example config path

- **State:** corrected; no scientific effect
- **Observation:** an inspection command requested `configs/small_cpu/` instead
  of the released `configs/small_cpu_example/` path.
- **Disposition:** listed the config tree and reran against the exact path.

### LRS-LOCAL-003 — incorrect arXiv TeX root filename

- **State:** corrected; no scientific effect
- **Observation:** a citation inventory command requested `main.tex`; the
  extracted source names the root `arxiv-main.tex`.
- **Disposition:** enumerated the source root and reran against the exact file.

### LRS-LOCAL-004 — unsupported local `hf` output option

- **State:** corrected; no scientific effect
- **Observation:** the installed `hf` CLI is version 1.5.0 and does not accept
  the documented `--format json` option for `hf models info`.
- **Disposition:** inspected local help and consumed the command's default JSON
  output. Model revisions were resolved successfully.

### LRS-LOCAL-005 — queried a nonexistent upstream tests directory

- **State:** corrected; no scientific effect
- **Observation:** a bounded source search included `upstream/tests`, which is
  absent from the released tree.
- **Disposition:** retained the error and restricted subsequent searches to
  paths present in the pinned source tree.

### LRS-LOCAL-006 — invoked tests with an unprepared system Python

- **State:** corrected; no scientific effect
- **Observation:** the first repository test command used `/usr/bin/python`,
  which did not have `pytest` installed.
- **Disposition:** created an ignored test environment from
  `requirements-test.txt` and reran the suite.

### LRS-LOCAL-007 — incorrectly requested a frozen root `uv` run

- **State:** corrected; no scientific effect
- **Observation:** a follow-up command passed `--frozen` at the NULSPEC site
  root, which has no `uv.lock`. `uv` created an empty ignored `.venv` and then
  stopped before installing or running anything.
- **Disposition:** installed the pinned test requirements directly into that
  ignored environment. The subsequent suite ran 45 tests: 44 passed and one
  unrelated legacy-protocol test lacked its intentionally external upstream
  result fixture in this new worktree. CI reconstructs that fixture before its
  test step.

### LRS-LOCAL-008 — assumed the experiment issue label existed

- **State:** corrected; no scientific effect
- **Observation:** the first attempt to register the artifact smoke run asked
  GitHub to apply the `experiment` label named by the repository's own issue
  template. That label is not configured in the repository, so GitHub rejected
  the request and created no issue.
- **Disposition:** verified that no partial issue existed, then created issue
  #27 without a label. No run began before successful registration.

### LRS-LOCAL-009 — invoked a non-executable Python helper directly

- **State:** corrected; no scientific effect
- **Observation:** the first post-smoke hashing command attempted to execute
  `hash_artifact_tree.py` directly even though it is intentionally not marked
  executable. All three hashing calls stopped with permission errors before
  writing manifests.
- **Disposition:** reran the helper through the pinned Python interpreter; all
  artifact manifests were created and validated.

### LRS-LOCAL-010 — clean-check did not account for documented generated paths

- **State:** corrected before primary compute; no scientific effect
- **Observation:** the post-preparation preflight rejected the pinned upstream
  checkout because ordinary imports created untracked Python bytecode. The
  local smoke example had likewise created untracked `.data/` and `.runs/`
  directories. No tracked source changed.
- **Disposition:** no primary GPU job began. The validator now allows only the
  upstream's three known generated path classes (`.venv`, `.data`/`.runs`, and
  `__pycache__`) and still rejects tracked changes or any other untracked path.
  Preparation and run environments now disable new bytecode writes.

### LRS-LOCAL-011 — repository guard rejected temporary cleanup syntax

- **State:** corrected; no scientific effect
- **Observation:** a citation-inventory determinism check included an automatic
  `rm -rf` cleanup trap scoped to a newly created temporary directory. The
  command safety guard rejected the entire shell command before execution.
- **Disposition:** reran the comparison without an explicit deletion command;
  the operating system may reclaim the isolated temporary directory normally.

### LRS-LOCAL-012 — source search included a nonexistent root path

- **State:** corrected; no scientific effect
- **Observation:** a repository-wide search for prior analysis patterns also
  named a conventional `src/` directory that this repository does not have.
  `rg` reported that missing path while still returning matches from every
  existing requested directory.
- **Disposition:** subsequent searches use paths confirmed by `rg --files`.

### LRS-LOCAL-013 — DOI failure was initially misdiagnosed as a relative redirect

- **State:** corrected after the second acquisition attempt; no scientific effect
- **Observation:** the first citation-acquisition attempt rejected two Project
  Euclid DOI redirects. The initial diagnosis called them relative redirects
  and added safe relative-URL resolution. Response-header inspection after the
  second attempt showed that both redirects were actually absolute HTTP
  downgrades, which the safety policy correctly continued to reject.
- **Disposition:** preserve both incomplete attempts and the corrected
  diagnosis. Keep relative redirect validation as a general safety fix, but use
  identity-matched archival Project Euclid PDFs for these two sources.

### LRS-LOCAL-014 — ad hoc archive query did not isolate per-item timeouts

- **State:** corrected; no scientific effect
- **Observation:** a read-only query for four Internet Archive capture records
  timed out on its third item and stopped before querying the fourth.
- **Disposition:** retained the partial output and queried the two remaining
  identifiers separately with bounded retries. No acquisition record or source
  selection was overwritten.

### LRS-LOCAL-015 — archive response was passed to JSON parser unchecked

- **State:** corrected; no scientific effect
- **Observation:** one exploratory Internet Archive loop passed a transient
  non-JSON response directly to `jq`, which exited with a parse error after the
  first of two lookups had succeeded.
- **Disposition:** queried the remaining URL separately with retries and JSON
  validation. No source or acquisition record was overwritten.

### LRS-LOCAL-016 — citation schemas were omitted from the first protocol tag

- **State:** corrected prospectively before model review; no scientific effect
- **Observation:** citation-audit protocol v1.0.0 required Qwen to return a
  "registered JSON schema," but the tagged protocol did not contain the schema
  files, packet-construction rules, or fixed structural-retry budget.
- **Disposition:** no Qwen citation prompt had been issued and no review result
  existed. Preserve the v1.0.0 tag, add the missing machine-readable contracts
  and deterministic packet builder in amendment v1.0.1, and tag that amendment
  before calibration. Do not backdate the added files into v1.0.0.

### LRS-LOCAL-017 — packet chunker admitted a newline past its byte ceiling

- **State:** corrected before model review; no scientific effect
- **Observation:** the first v1.0.1 packet-build attempt used an inclusive
  newline-search bound after finding the largest Unicode prefix under 48,000
  bytes. When the next character was a newline, the line-boundary preference
  included that extra byte and the builder's independent size assertion failed.
- **Disposition:** preserve the partial failed packet directory, change the
  search stop to the already validated exclusive boundary, add a regression
  test for the exact case, and build into a new append-only directory. No Qwen
  prompt was issued from the failed attempt.

### LRS-LOCAL-018 — local shell interpreted documentation-search backticks

- **State:** corrected; no scientific effect
- **Observation:** one read-only SSH documentation search placed Markdown
  backticks inside a double-quoted shell argument. The local shell attempted to
  execute the two enclosed endpoint names, printed command-not-found messages,
  and then completed the harmless remote search.
- **Disposition:** no files or services changed. Reran the exact documentation
  inspection using a single-quoted remote command and avoid executable quoting
  syntax in subsequent shell arguments.

### LRS-LOCAL-019 — stream test exposed an HTTP socket ownership assumption

- **State:** corrected before model review; no scientific effect
- **Observation:** the first mocked SSE transport test used an HTTP/1.0 test
  peer. Python transferred the active socket from `HTTPConnection` to the
  response object, so the runner's timeout setter incorrectly reported that
  the connection had lost its socket before reading the first event.
- **Disposition:** resolve the active socket from either connection ownership
  location. If an HTTP/1.0 close has already detached it, retain the timeout
  installed when the connection was opened (the frozen first-event and idle
  limits are equal) while continuing to enforce total elapsed time between
  reads. Retain the failing test output and rerun the streamed trace test. No
  Qwen service was started or called.

### LRS-LOCAL-020 — broad workstation model search was stopped

- **State:** stopped; no scientific effect
- **Observation:** a read-only search for an optional workstation llama binary
  and GGUF traversed too broad a Windows-mounted directory and produced no
  result within 30 seconds.
- **Disposition:** terminated the search without changing any file or process.
  Subsequent workstation discovery must use indexed file lists or known model
  roots and is not allowed to delay or compete with the primary run.

### LRS-LOCAL-021 — dynamic provider-test module was not registered

- **State:** corrected before provider or teacher invocation; no scientific effect
- **Observation:** the first offline provider-contract test loaded the module
  with `importlib` but did not add it to `sys.modules` before execution. Python
  3.12's dataclass decorator consequently failed during test collection.
- **Disposition:** register the temporary module under its spec name before
  execution and rerun the unchanged provider assertions. No network request,
  model review, experimental artifact, or service was affected.

### LRS-LOCAL-022 — copied llama binary was incompatible with workstation libc

- **State:** diagnosed before server start or GPU allocation; no scientific effect
- **Observation:** the exact dev-box llama.cpp binary and shared libraries were
  staged to the workstation, but a read-only version check showed that they
  require glibc 2.38 and `GLIBCXX_3.4.32`; the workstation exposes glibc 2.35
  and an older libstdc++. The model file itself transferred and hashed normally.
- **Disposition:** preserve the failed version output, build the same pinned
  llama.cpp commit natively on the workstation at low CPU/I/O priority, and
  require its commit/version plus the GGUF hash in the eventual Qwen trace.
  No llama server was started and the workstation GPU remained untouched.

### LRS-LOCAL-023 — teacher event writer initially emitted pretty-printed JSON

- **State:** corrected during offline implementation; no execution or scientific effect
- **Observation:** the first unexecuted draft of the external-teacher runner
  reused the pretty-printed artifact serializer for its event stream, which
  would have produced multi-line JSON records instead of JSON Lines.
- **Disposition:** use a dedicated compact, one-object-per-line event encoder
  and cover the emitted format in offline tests before any provider call.

### LRS-LOCAL-024 — Qwen trace omitted the llama-server executable hash

- **State:** corrected prospectively before Qwen review; no scientific effect
- **Observation:** citation-audit runner v1.0.1 captured the llama.cpp version
  output and live route properties but did not record the executable's byte
  count and SHA-256. This was found while preparing a native workstation build;
  no Qwen citation request had yet occurred.
- **Disposition:** retain the v1.0.1 tag, add the executable identity fields in
  trace-only amendment v1.0.2, test the record, and freeze a new harness tag.
  Evidence packets, prompts, schemas, model, and generation settings are unchanged.

### LRS-LOCAL-025 — Qwen identity test omitted the scripts import path

- **State:** corrected during offline testing; no scientific effect
- **Observation:** the first dynamic import in the new executable-identity test
  did not add the repository's `scripts/` directory to `sys.path`, so collection
  could not resolve the runner's sibling contract module.
- **Disposition:** add the same scripts-directory path available during normal
  command-line execution and rerun the unchanged identity assertion. No service,
  model process, review artifact, or experimental result was affected.

### LRS-LOCAL-026 — Track M base input lacked a content manifest

- **State:** corrected prospectively before every Track M and 1.5B arm; no result effect
- **Observation:** primary runner v1.0.0 recorded which Track R base directory a
  Track M arm reused, but did not hash the files in that trained-model input.
  This became material when preparing a byte-exact copy for a second host. The
  first Track R 0.5B arm was already active when the gap was identified.
- **Disposition:** do not mutate the active attempt. Add a read-only input-tree
  manifest plus source arm/attempt record to harness amendment v1.0.1, freeze it
  before Track M, and separately audit the active Track R base after completion.
  No data, model parameter, training command, metric, or interpretation changes.

### LRS-LOCAL-027 — calibration inventory probe assumed inline chunks

- **State:** corrected; no scientific effect
- **Observation:** a read-only ad hoc calibration inventory probe attempted to
  read `chunks` from each top-level review-plan source entry. The plan instead
  stores a hash-bound `source_plan_relative_path`, and the probe stopped with a
  `KeyError` after printing the first source summary.
- **Disposition:** load each referenced immutable source plan and inspect its
  chunk list there. No packet, source, trace, model process, or result changed.

### LRS-LOCAL-028 — jq fallback indexed the inventory object as an array

- **State:** corrected; no scientific effect
- **Observation:** a read-only schema probe combined several jq fallback
  expressions, one of which still evaluated a numeric index against the
  top-level citation-inventory object and exited with a type error after
  correctly printing its keys.
- **Disposition:** address the named `records` and `citation_occurrences` fields
  directly. No inventory, expectation, packet, or result was modified.

### LRS-LOCAL-029 — named inventory fields were also assumed to be arrays

- **State:** corrected; no scientific effect
- **Observation:** the immediate follow-up read-only jq probe addressed the
  correct field names but again indexed them numerically without first checking
  their types; the fields use non-array shapes and jq stopped with a type error.
- **Disposition:** inspect top-level value types before selecting nested data,
  then build the expectation test from the actual schema. No file changed.

### LRS-LOCAL-030 — implementation audit included a nonexistent `src/` path

- **State:** corrected; no scientific effect
- **Observation:** a read-only file inventory assumed a conventional upstream
  `src/` directory alongside `experiments/`. The repository has no `src/`, so
  `find` reported that path while still listing the actual experiment modules.
- **Disposition:** constrain subsequent audits to the discovered upstream tree.
  No upstream file, environment, trace, or result changed.

### LRS-LOCAL-031 — follow-up inventory omitted the ignored work prefix

- **State:** corrected; no scientific effect
- **Observation:** a read-only follow-up inventory queried
  `research/replications/2607.17674/upstream`, omitting the repository's ignored
  `work/` directory component. `rg` stopped with a missing-path diagnostic.
- **Disposition:** use the already discovered
  `research/replications/2607.17674/work/upstream` path and include ignored
  files explicitly when inventorying immutable working copies. No upstream
  file, environment, trace, process, or result changed.

### LRS-LOCAL-032 — module inventory guessed a separate evaluation directory

- **State:** corrected; no scientific effect
- **Observation:** a read-only module inventory included
  `experiments/evaluation`, but the released implementation keeps its
  evaluation modules inside `experiments/factorization`. `rg` diagnosed only
  the nonexistent extra path and still returned the two valid trees.
- **Disposition:** inventory only paths first identified from the complete
  upstream file list. No upstream file, environment, trace, process, or result
  changed.

### LRS-LOCAL-033 — test search assumed an upstream `tests/` directory

- **State:** corrected; no scientific effect
- **Observation:** a read-only search for coverage of a suspected sequence-mask
  edge case targeted `tests/` before verifying that the pinned upstream tree
  contains such a directory. `rg` stopped with a missing-path diagnostic.
- **Disposition:** inventory the tree before any narrower test search and use a
  self-contained read-only probe if upstream coverage is absent. No upstream
  file, environment, trace, process, or result changed.

### LRS-LOCAL-034 — unrelated protocol test required an absent ignored fixture

- **State:** isolated; no scientific effect
- **Observation:** an over-broad verification command included the repository's
  earlier-study `tests/test_protocol.py`. One test requires an ignored
  `paper_repro/SLM-RL-Agents/results/all_results.json` fixture that is not
  present in this worktree, so the combined command ended after 18 passes and
  that unrelated missing-file failure.
- **Disposition:** record the failure and run the new evaluator tests, matrix
  analyzer tests, and 2607.17674 protocol validator as separate scoped checks.
  No artifact, process, metric, or source file was altered by the failed read.

### LRS-LOCAL-035 — trace analyzer draft retained an unused type import

- **State:** corrected before commit or scientific use; no result effect
- **Observation:** the first static check of the new instrumented-evaluation
  analyzer rejected an unused `Iterable` import after formatting.
- **Disposition:** remove the unused import and rerun formatting, lint, and the
  analyzer/evaluator tests. No trace, primary process, or analysis ran through
  the rejected draft.

### LRS-LOCAL-036 — trace validator initially treated row counts as probabilities

- **State:** corrected before commit or scientific use; no result effect
- **Observation:** the first analyzer unit run reached the recomputation checks
  but sent integer `num_examples` and `num_pairs` fields through the `[0, 1]`
  probability validator. Two synthetic tests failed on the count value `2`.
- **Disposition:** validate recomputed counts by exact integer equality, retain
  bounded checks for rates, and rerun the entire new test pair. No experimental
  trace or primary artifact was supplied to the draft analyzer.

### LRS-LOCAL-037 — live-metric probe used guessed key names

- **State:** corrected; no scientific effect
- **Observation:** a read-only `jq` summary of the active factorization log
  queried plausible but nonexistent generation and optimization key names. The
  command succeeded with `null` diagnostics while correctly reading the loss
  fields.
- **Disposition:** inspect the row's exact key inventory and repeat the summary
  with `sampled_val/*` and `optimization/window/*` names. No run file, process,
  checkpoint, or metric was changed.

### LRS-LOCAL-038 — theory-source search used an incomplete local path

- **State:** corrected immediately; no scientific effect
- **Observation:** a read-only theory audit first queried
  `upstream/paper/sections/` at the repository root, although the frozen arXiv
  source is stored under `research/replications/2607.17674/work/sources/`.
- **Disposition:** locate the exact ignored source path with a file inventory
  before continuing the audit. No run file, process, checkpoint, or source was
  changed.

### LRS-LOCAL-039 — preflight hash process handle was not retained

- **State:** contained; no scientific effect
- **Observation:** a read-only workstation preflight began hashing the 16.5 GB
  Qwen GGUF, but the orchestration wrapper printed only incremental command
  output and omitted the returned terminal-session identifier while the hash
  was still running.
- **Disposition:** observe the identifiable `sha256sum` process to normal
  completion and retain structured session metadata for subsequent long-lived
  commands. The registered model had already been hashed independently; no
  model, trace, service, or primary process was changed.

### LRS-LOCAL-040 — first citation-packet transfer lacked its ignored parent

- **State:** corrected before transfer or review; no scientific effect
- **Observation:** the first bounded `rsync` into the new dev-box citation
  checkout failed with code 11 because a clean clone does not contain the
  ignored `research/replications/2607.17674/work/` parent tree.
- **Disposition:** create only the exact packet parent, repeat the non-deleting
  transfer, and compare deterministic source/destination inventories before
  use. The failed call created no packet and no reviewer request was made.

### LRS-LOCAL-041 — citation teacher manifest used a JSON boolean in Python

- **State:** corrected before a production teacher packet; no scientific effect
- **Observation:** merge validation found lowercase `false` in the Python
  manifest builder's local-model provenance object. That branch would raise
  `NameError` when it constructed a citation teacher packet, although existing
  tests did not exercise the affected statement.
- **Disposition:** replace it with Python `False`, retain the discovery in this
  log, and freeze citation-teacher harness amendment v1.0.3 with new bindings
  rather than rewriting v1.0.2. The focused packet-builder, GLM/Kimi runner,
  Codex runner, and trace-validator tests pass. No reviewer request, result,
  trace, or primary experiment was created or changed by this correction.

### LRS-LOCAL-042 — citation response schema exceeded llama.cpp grammar limits

- **State:** attempt preserved and rejected; correction required before retry
- **Observation:** the pinned llama.cpp server rejected the full evidence JSON
  Schema because nested bounded repetitions exceeded its grammar parser's sane
  expansion limit. It then served the request without the intended grammar.
  The harness had tested schema validation and streaming independently but had
  not preflighted this exact schema-to-grammar conversion against the pinned
  runtime.
- **Disposition:** stop the calibration gate, preserve both invalid request
  traces, and amend the transport only after an exact-runtime regression test.
  Client-side canonical-schema validation remains mandatory. No citation
  review, teacher input, primary metric, or publication artifact was accepted.

### LRS-LOCAL-043 — unsupported preflight switch launched an authorized arm

- **State:** contained; no scientific deviation
- **Observation:** the workstation launch prefixed the current study's guarded
  runner with `PREFLIGHT_ONLY=1`, assuming support equivalent to the preceding
  study's runner. This script does not interpret that variable and therefore
  launched the exact registered Track M 0.5B arm after its normal guards.
- **Disposition:** retain the immutable attempt because this was the next
  explicitly authorized arm, on the intended GPU, commit, inputs, and limits.
  Record that it was an actual launch from inception and do not describe it as
  a preflight. Future read-only checks must use only switches implemented by
  the selected study runner.

### LRS-LOCAL-044 — forwarded interrupt did not stop the remote review scope

- **State:** corrected; no scientific effect
- **Observation:** forwarding `Ctrl-C` through the retained SSH terminal closed
  the client connection, but the separately managed remote llama-server scope
  remained active and idle.
- **Disposition:** stop the exact research-owned scope through the user service
  manager and verify its PID, host memory, and GPU allocation disappeared.
  No unrelated process was signalled; the primary run and unrelated service
  remained healthy.

### LRS-LOCAL-045 — error-ledger patch used stale neighboring text

- **State:** corrected before any file change; no scientific effect
- **Observation:** the first patch for entries 042–044 assumed entry 040 was
  still adjacent to the external-limitations section. Another valid entry had
  since been added, so `apply_patch` rejected the entire multi-file patch.
- **Disposition:** reread the exact current ledger, preserve the intervening
  entry, and reapply against a unique current anchor. The rejected patch made
  no source, trace, run, or artifact change.

### LRS-LOCAL-046 — live run checkout was briefly dirtied by documentation

- **State:** corrected before evaluation or terminal capture; no code effect
- **Observation:** entries 042–045 and the citation execution note were first
  drafted in the clean checkout hosting the newly active Track M arm. No
  protocol, runner, upstream source, config, or environment file was edited,
  but the terminal manifest would have recorded a dirty documentation tree.
- **Disposition:** move the exact edits into a named recoverable stash, verify
  the execution checkout returned to its launch commit with an empty status,
  and continue all maintenance in a separate clone. The start manifest was
  already clean; the stash remains retained until the separate-clone commit is
  verified.

### LRS-LOCAL-047 — citation packet probe guessed an extra directory

- **State:** corrected immediately; no scientific effect
- **Observation:** a read-only `jq` probe first looked for the Allman evidence
  packet under an extra `sources/` component. The exact packet inventory uses
  `packets/{citation_key}/evidence/`.
- **Disposition:** inventory the frozen packet root and repeat the query at the
  exact path. No packet, trace, schema, or review was changed.

### LRS-LOCAL-048 — selected experiment environment lacked pytest

- **State:** corrected before commit; no scientific effect
- **Observation:** the first focused harness-test command selected the frozen
  upstream experiment environment, which intentionally lacks `pytest`. The
  command exited before running any test or later chained check.
- **Disposition:** use the host's registered test runner for repository tests,
  while retaining the frozen upstream Python only for the upstream protocol
  validation command.

### LRS-LOCAL-049 — citation runner retained an unused import

- **State:** corrected before commit or retry; no scientific effect
- **Observation:** focused tests passed, then Ruff found the merged citation
  runner still imported `os` without using it.
- **Disposition:** remove the import and rerun the complete focused tests,
  lint, and protocol validator. No Qwen request used the amended runner.

### LRS-LOCAL-050 — runtime-amendment draft needed formatter normalization

- **State:** corrected before commit or retry; no scientific effect
- **Observation:** eleven focused tests and Ruff lint passed, but Ruff's
  formatting check identified the amended runner and test module as not yet in
  canonical layout.
- **Disposition:** apply the repository formatter mechanically, then rerun all
  eleven focused tests, lint, and the formatting check. No request, trace, or
  primary run used the unformatted draft.

### LRS-LOCAL-051 — concurrency-lock handle was not referenced after acquisition

- **State:** corrected before commit or citation retry; no scientific effect
- **Observation:** Ruff correctly rejected the first citation concurrency-lock
  patch because its retained handle was assigned only for lifetime semantics
  and was not referenced later in the function.
- **Disposition:** bind the handle's open state into the private run-input
  record, making both the retention and trace semantics explicit, then rerun
  lint and the focused tests. No citation request used the draft.

### LRS-LOCAL-052 — direct lock probe omitted the scripts import path

- **State:** corrected immediately; no scientific effect
- **Observation:** the first read-only contention probe loaded the citation
  runner by file path without first adding its sibling scripts directory to
  Python's import path. Import stopped at `citation_review_contract` before the
  lock probe ran.
- **Disposition:** repeat the probe with the same import setup used by the test
  suite. The failure created no trace and contacted no model route.

### LRS-LOCAL-053 — maintenance checkout lacked the ignored upstream environment

- **State:** corrected before commit; no scientific effect
- **Observation:** a chained validation command addressed the frozen upstream
  virtual environment beneath the maintenance checkout, whose ignored work
  tree intentionally contains no model or environment staging. Citation tests,
  lint, and formatting had already passed; only the final protocol-validator
  command did not start.
- **Disposition:** run the tracked validator from the maintenance checkout with
  the absolute frozen upstream tree and Python environment in the active
  execution checkout. No generated experiment artifact was read or changed.

### LRS-LOCAL-054 — PR status query requested an unsupported field

- **State:** corrected immediately; no scientific effect
- **Observation:** a read-only GitHub CLI query requested `headRefOid`, which
  is not exposed by the installed `gh pr view` JSON field set. The preceding
  check query still reported both required checks as passing.
- **Disposition:** query the supported commit list and select its final OID.
  The corrected read confirmed the draft PR was clean at the expected branch
  commit. No repository or pull-request state changed.

### LRS-LOCAL-055 — service-health probe assumed a nonexistent log path

- **State:** corrected immediately; no scientific or service effect
- **Observation:** a read-only service-health probe inferred a live log path
  from a crash-handler attachment argument, but no file existed at that path.
  The command stopped at `stat` and did not inspect or change the service.
- **Disposition:** use process and service state plus the actual rolling world-
  save and backup artifacts for the non-experimental service health check. The
  corrected probe confirmed current saves and backups without issuing a server
  command.

### LRS-LOCAL-056 — schema preflight did not acquire the host experiment lock

- **State:** preserved and prospectively corrected; no scientific result
- **Observation:** the first exact-runtime transport-schema preflight ran on
  the same host and GPU as the active primary arm. It made two one-token parser
  requests and no citation judgment, but it did not acquire the host-wide
  experiment lock and therefore violated the resource policy.
- **Disposition:** retain the complete trace as diagnostic-only evidence and do
  not treat it as an eligible reference execution. Preflight v1.0.1 acquires
  and records the shared lock before route inspection, trace creation, or a
  request. Require a fresh uncontended pass before replacement calibration.

### LRS-LOCAL-057 — primary run manifests could not invoke pip freeze

- **State:** preserved and prospectively corrected; provenance-only
- **Observation:** the active R and M 0.5B start manifests recorded an empty
  package list with `package_capture_exit_code = 1`. The exact `uv`-managed
  paper environment has no `pip` module, so `python -m pip freeze --all`
  returned `No module named pip`. Python, CUDA, repository, upstream, config,
  matrix, source, and lockfile identities remained available, and training was
  unaffected.
- **Disposition:** never rewrite either start manifest. Harness v1.0.2 records
  the failed pip attempt and falls back to `importlib.metadata`, and it writes a
  separate self-hashing Python-environment inventory before future arms. Add
  the same inventory as a labeled post-run supplement to each active attempt.

### LRS-LOCAL-058 — package-inventory patch needed formatter normalization

- **State:** corrected before commit or use; no scientific effect
- **Observation:** Ruff lint passed, then its formatting check identified the
  manifest helper and two focused test modules as not yet in canonical layout.
  The chained tests therefore did not start in that command.
- **Disposition:** apply the repository formatter mechanically, then rerun
  lint, formatting, and all focused tests. Neither active arm loads the
  maintenance checkout, and no run manifest used the draft.

### LRS-LOCAL-059 — cross-study full suite lacked an ignored result fixture

- **State:** isolated; no effect on this study
- **Observation:** the repository-wide test run passed 158 tests and failed one
  test for a different study because the clean maintenance checkout does not
  contain its ignored `all_results.json` fixture. The five package-inventory
  and primary-input focused tests had already passed.
- **Disposition:** retain the failure as an environment limitation, rely on the
  focused tests and frozen protocol validator for this amendment, and require
  the normal GitHub workflow—which provisions its own fixtures—to pass. Do not
  copy an unrelated private result into this checkout merely to satisfy the
  local full suite.

### LRS-LOCAL-060 — terminal-trap test needed formatter normalization

- **State:** corrected before commit or use; no scientific effect
- **Observation:** Ruff lint passed, then its formatting check identified the
  focused runner-order test changed in the terminal-trap review. The chained
  tests did not start in that command.
- **Disposition:** format the test mechanically and rerun lint, formatting,
  shell syntax, and the focused tests. Active arms remain bound to their clean
  original checkouts and did not load this draft.

### LRS-LOCAL-061 — Track M 0.5B exceeded the workstation GPU memory

- **State:** terminal attempt preserved; no scientific result
- **Observation:** the exact registered Track M Qwen2.5-0.5B arm generated all
  120,000 model responses, then raised a CUDA out-of-memory error during
  `c_theta` estimation before its first factorization optimizer step. The 24 GB
  RTX 4090 had ample host RAM behind its 22/26 GiB high/max process guards; the
  failure was device-memory exhaustion, not a host-memory or service guard.
- **Disposition:** retain the failed manifest, full logs, sampled-response
  Parquet files, post-run artifact manifest, and supplemental package inventory.
  Assign no endpoint metric or paper-level evidentiary weight. Do not change the
  batch, precision, vocabulary, model count, or objective to make it fit; use a
  fresh exact attempt on the 96 GB card.

### LRS-LOCAL-062 — copied llama-server build was not ABI-portable

- **State:** contained before model load or citation request
- **Observation:** while staging the idle workstation for citation review, we
  copied the pinned llama.cpp CUDA build produced on the newer dev-box OS. The
  executable could not start on the workstation because it required
  `GLIBC_2.38` and `GLIBCXX_3.4.32`, which that older host does not provide.
  The registered GGUF copied successfully and its SHA-256 matched; no model was
  loaded, route opened, evidence packet inspected, trace directory created, or
  citation request sent.
- **Disposition:** retain this as our staging error. Build llama.cpp commit
  `f53577432541bb9edc1588c4ef45c66bf07e4468` natively on the workstation for
  compute capability 8.9, record the resulting executable hash and version,
  and require the ordinary uncontended runtime preflight before calibration.

### LRS-LOCAL-063 — first workstation calibration command used the packet subdirectory

- **State:** contained before lock acquisition, trace creation, or model request
- **Observation:** after the eligible runtime preflight passed, the first
  calibration invocation supplied the generated `packets/` directory as
  `--packet-root`. The validator expects its immutable attempt parent because
  the review plan already stores paths beginning with `packets/`; validation
  therefore looked for `packets/packets/...` and raised `FileNotFoundError`.
- **Disposition:** record the failed command as our path-selection error. The
  requested trace root remained absent and the experiment lock was free. Use a
  new invocation identifier with the immutable packet-attempt parent as
  `--packet-root`; do not assign this pre-request failure evidentiary weight.

### LRS-LOCAL-064 — dev-box fan daemon retained the pre-upgrade GPU mapping

- **State:** mitigated; durable script corrected, privileged service restart pending
- **Observation:** the root fan daemon still assumed that `nvidia-smi` index 0
  was the same device as X fan targets 0 and 1. After the hardware change those
  orders diverged: the idle RTX 3090 temperature controlled the PRO 6000 fans,
  while the loaded PRO 6000 temperature controlled the 3090 fan. During the
  released-arm final evaluator, the 500 W PRO 6000 reached 93 C and briefly
  entered NVIDIA software thermal slowdown. There was no Xid, CUDA failure,
  process interruption, memory pressure, or unrelated-service restart.
- **Disposition:** a passwordless power-limit change was unavailable and made no
  change. Back up the original 2,438-byte script (SHA-256
  `7fe5f63af711bd5236e7b8f872e03998d87b88554d1e773c3343592296e4ba2a`),
  replace index inference with immutable GPU UUIDs, validate the shell syntax,
  and retain the corrected 3,245-byte script with SHA-256
  `1a2da6244f044639c0e48da23f6e4eb3524e6ba7b0c98dc5820d996e3eaf2ec1`.
  A user-level reconciliation guard applies the corrected curve until an
  administrator restarts the root service or the host reboots. At full load the
  card returned below 80 C without changing experimental code or data.

### LRS-LOCAL-065 — eligible Qwen calibration altered PDF evidence locators

- **State:** terminal zero-weight attempt; prospective presentation amendment frozen
- **Observation:** runtime v1.0.2 passed an uncontended exact-schema preflight,
  but both permitted Qwen generations failed on the first Allman et al. chunk.
  The reviewer removed line-wrap hyphens from verbatim excerpts and/or inferred
  page numbers from document position rather than the packet's exact page spans.
  The registered validator rejected three candidates in attempt 1 and five in
  attempt 2. No evidence record, synthesis, final review, or teacher input was
  accepted.
- **Disposition:** preserve the 23-file trace and assign it no citation weight.
  Do not relax exact grounding. Runtime v1.0.3 instead supplies a model-facing
  page-labeled view derived losslessly from the same immutable packet and a
  hash-bound instruction to preserve line-wrap hyphens. All 112 frozen packets
  pass the presentation coverage check; a new calibration requires a fresh
  trace and lock-held preflight.

### LRS-LOCAL-066 — first focused-test invocations used unsuitable local defaults

- **State:** contained before commit or runtime use
- **Observation:** the first workstation test command selected system Python,
  which did not have `pytest`. The isolated environment was then populated
  piecemeal and its first repository-wide collection lacked the pinned `scipy`
  dependency. After installing `requirements-test.txt` exactly, the suite
  reached 161 passes and only the unrelated missing fixture already recorded in
  LRS-LOCAL-059. An unrestricted latest-Ruff invocation also enabled rules that
  flag retained pre-existing exception-handling and line-length choices outside
  this change. None of these failed commands produced a test pass or changed a
  research artifact.
- **Disposition:** retain these as our verification-command errors. Use the
  isolated environment populated from the frozen test requirements, apply only
  deterministic import/format fixes, run the repository's scoped `E`, `F`, and
  `I` checks with the existing line-length exception, and report the actual
  focused-test result separately.

### LRS-LOCAL-067 — first v1.0.3 calibration wrapper combined incompatible flags

- **State:** contained before scope creation, trace creation, lock acquisition,
  or model request
- **Observation:** the first prospective calibration wrapper combined
  `systemd-run --scope` with `--wait`. The local systemd version rejects that
  combination immediately, so the command exited before the citation runner
  started.
- **Disposition:** preserve this as our launch-command error. Remove only the
  incompatible wrapper flag and use fresh unit and trace identifiers for the
  otherwise identical registered calibration command.

### LRS-LOCAL-068 — local GitHub CLI lacked a requested list filter

- **State:** corrected in the read-only CI check; no research effect
- **Observation:** the installed `gh run list` version does not implement its
  newer `--branch` option, so the first CI-status query exited before returning
  runs.
- **Disposition:** retain this as our tooling-assumption error. Query the same
  read-only run list using supported fields and filter the exact commit SHA
  locally. The tagged v1.0.3 commit's CI run then returned `success`.

### LRS-LOCAL-069 — page labels did not prevent Qwen from repairing PDF words

- **State:** terminal zero-weight v1.0.3 attempt; further same-contract retries blocked
- **Observation:** v1.0.3 fixed the earlier page-locator errors and several
  evidence candidates grounded exactly, but both allowed generations still
  silently joined words split by retained physical line-wrap hyphens. The
  unchanged validator rejected two candidates in each attempt. No accepted
  evidence, synthesis, final review, or teacher input was produced.
- **Disposition:** preserve the full trace and assign it no citation weight.
  Do not weaken grounding or rerun v1.0.3. Any next attempt must prospectively
  constrain excerpts to exact single-line source spans, retain the immutable
  packet and original invalid outputs, pass new coverage tests and an eligible
  preflight, and use a fresh trace identifier.

### LRS-LOCAL-070 — 1.5B readiness check assumed a display-name directory

- **State:** corrected before run launch; no experimental effect
- **Observation:** the first read-only 1.5B readiness command looked for a
  `snapshot-`-prefixed model directory, matching the inventory filename rather
  than the actual revision-named snapshot directory. The fail-closed compound
  check exited silently before acquiring the experiment lock or starting a run.
- **Disposition:** retain this as our path-assumption error. Resolve the model
  directory from the frozen protocol/revision, rerun every readiness check, and
  launch only after the corrected exact path and all service/resource gates pass.

### LRS-LOCAL-071 — first v1.0.4 format check found one wrapping difference

- **State:** corrected before commit, tag, preflight, or model request
- **Observation:** focused tests and scoped lint passed, while Ruff's formatting
  check requested a mechanical single-line normalization in the preflight
  version error. No runtime behavior or research artifact used that draft.
- **Disposition:** apply Ruff's deterministic formatter and rerun formatting,
  lint, focused tests, all-packet coverage, and context-size checks before
  freezing the amendment.

### LRS-LOCAL-072 — first exact-line representation exceeded model context

- **State:** rejected before commit, tag, preflight, or model generation
- **Observation:** the first v1.0.4 draft attached a line number and SHA-256 to
  every physical source line. The mandatory all-packet tokenizer audit found a
  52,877-token median prompt and a 99,609-token maximum before output reserve,
  exceeding the live 50,176-token context. No citation decision used it.
- **Disposition:** retain this as our prospective design error. Use compact
  ordered arrays of exact line strings, preserve integrity with the existing
  page SHA-256 plus fail-closed concatenation, and rerun all 112 packets. The
  replacement maximum is 35,644 exact rendered-prompt tokens and 43,836 after
  the full 8,192-token output reserve.

### LRS-LOCAL-073 — context-audit documentation patches used wrong context

- **State:** atomically rejected and corrected; no research effect
- **Observation:** the first documentation-only patch placed an error-log
  context under the execution-record file header. A later preflight-record
  patch assumed a sentence began on a new line when it followed the prior
  sentence on that line. `apply_patch` rejected both entire patches because
  their contexts did not exist, so no file was partially modified.
- **Disposition:** retain this as our editing-command error and reapply with an
  explicit update header for each file. Recheck whitespace and exact hashes
  before commit.

### LRS-LOCAL-074 — symbolic branch refspec failed after the v1.0.4 commit

- **State:** corrected before remote synchronization or runtime use
- **Observation:** the v1.0.4 commit and annotated tag were created locally,
  then the first push reported that the symbolic branch refspec did not match,
  even though the checked-out branch and local head ref both existed. No branch
  or tag reached the remote in that failed command.
- **Disposition:** verify the exact local commit, branch, and tag, then push the
  immutable commit using the explicit `HEAD:refs/heads/...` refspec and push the
  exact tag ref separately. Both succeeded before checkout synchronization,
  preflight, or calibration.

### LRS-LOCAL-075 — Qwen server cgroup stalled the v1.0.4 calibration

- **State:** contained; failed trace preserved with zero decision weight
- **Observation:** the workstation reviewer scope was launched with 8 GiB
  `MemoryHigh`, 12 GiB `MemoryMax`, and a 2 GiB swap maximum. After two accepted
  evidence chunks grew the runtime prompt cache, neither request for Allman
  chunk 3 emitted a response byte before the 120-second first-event deadline.
  Terminal inspection found 105,483 high-limit events, the full swap allowance
  consumed, severe cgroup memory pressure, and the process sleeping in
  `mem_cgroup_handle_over_high`. There was no max-limit, OOM, or OOM-kill event.
- **Disposition:** attribute the outcome to our local resource envelope rather
  than Qwen or the cited source. Preserve the complete trace and server log,
  assign every partial record zero citation-decision weight, and launch a fresh
  replacement only after an uncontended preflight under a prospectively
  recorded larger envelope. Do not resume or overwrite the failed trace.

### LRS-LOCAL-076 — first repaired Qwen envelope still touched MemoryHigh

- **State:** caught before replacement calibration; corrected prospectively
- **Observation:** the first repair proposed 12/16 GiB high/max with 4 GiB
  swap. Immediately after model load and a one-token schema preflight,
  `MemoryCurrent` was within 81,920 bytes of `MemoryHigh`, and the new scope had
  already recorded 50,712 high-limit events. The runtime advertises an 8 GiB
  prompt-cache ceiling, so continuing could have reproduced the prior stall.
- **Disposition:** keep that successful schema preflight as diagnostic only,
  increase the still-pre-calibration scope to 20/24 GiB high/max, retain the
  4 GiB swap limit, and run a new exclusive-lock preflight. The final envelope
  remains below half of the workstation's 94 GiB physical memory. No
  citation-bearing request, primary metric, or unrelated service was affected.

### LRS-LOCAL-077 — replacement Qwen headroom was still too narrowly projected

- **State:** corrected before another high-limit event; disclosed operational
  adjustment, no scientific effect observed
- **Observation:** the replacement calibration began after a clean preflight
  under the 20/24 GiB high/max envelope. After its first evidence chunk, the
  server used 16,383,631,360 bytes while its advertised 8 GiB prompt cache was
  still accumulating source prompts. It remained below `MemoryHigh`, and the
  inherited high-event count had not increased, but the projected full-cache
  state left insufficient margin for a long review pass.
- **Disposition:** before a new high event, relax the live server to 32/40 GiB
  high/max, retain the 4 GiB swap and eight-core limits, and record the exact
  timing and cgroup state without canceling or restarting the in-flight
  request. The hard limit remains below half of physical workstation memory.
  This changes no model, route, packet, prompt, schema, validator, sampling
  parameter, response, or primary experiment.

### LRS-LOCAL-078 — new private-tree index script was not initially Ruff-formatted

- **State:** corrected before commit; no research effect
- **Observation:** the focused unit tests and Ruff lint passed, but Ruff's
  format check reported that the new deterministic private-tree index script
  required one mechanical formatting change.
- **Disposition:** apply Ruff formatting, rerun lint and the format check, and
  rerun all four focused tests. The final checks pass; no trace, hash input, or
  live process was changed.

### LRS-LOCAL-079 — PR inspection requested an unsupported old-gh JSON field

- **State:** corrected after the push; no repository or research effect
- **Observation:** the explicit `HEAD` push of commit `156cc4a` succeeded, but
  the chained read-only PR inspection requested `headRefOid`, which this host's
  older GitHub CLI does not expose. The inspection command exited nonzero after
  the remote update was already complete.
- **Disposition:** query only fields listed by the installed client and obtain
  the latest commit from the final item in its supported `commits` array. PR
  #26 then reported the expected head commit and two running checks.

### LRS-LOCAL-080 — calibration comparator used JSON booleans in Python source

- **State:** caught by lint and focused tests; corrected before commit or use
- **Observation:** the first draft of the frozen-expectation comparator wrote
  lowercase JSON literals in one Python dictionary. Ruff reported six
  undefined names, and two of three focused tests failed at that construction;
  no comparison artifact was written.
- **Disposition:** replace the six literals with Python booleans, rerun Ruff
  lint and formatting, compilation, and all focused tests before applying the
  comparator to a completed calibration. No live process or research artifact
  was affected.

### LRS-LOCAL-081 — CI inspection requested unsupported job detail from old gh

- **State:** corrected read-only query; no repository or research effect
- **Observation:** a post-push CI query requested the `jobs` field from this
  host's older GitHub CLI, which lists only run-level fields for `gh run view
  --json`. The command changed no local or remote state.
- **Disposition:** repeat the query with the supported run-level fields. CI run
  `30743847152` then reported `success` for exact head commit `156cc4a`.

### LRS-LOCAL-082 — accounting-helper checks first used the wrong Python route

- **State:** corrected before commit or trace accounting; no research effect
- **Observation:** the first focused-check invocation used the system Python,
  which does not contain `pytest` or Ruff. A second command also lacked shell
  fail-fast behavior, so its successful compilation step masked Ruff's
  nonzero format-check status even though the output plainly reported two
  files requiring formatting. No research trace or accounting artifact was
  read or written by either failed check.
- **Disposition:** use the registered shared development environment, run the
  formatter, and repeat lint, format verification, compilation, and all eleven
  focused tests under `set -e`. Every final check passes. Future chained check
  invocations must enable fail-fast behavior before the first validator.

### LRS-LOCAL-083 — first accounting draft rejected a no-response attempt

- **State:** corrected before commit or trace accounting; no research effect
- **Observation:** code review after the focused checks found that the first
  accounting-helper draft required every attempt to contain a transport
  object. The citation runner deliberately records `transport: null` when a
  request fails before a response is assembled, so that draft could not have
  summarized a terminal resource or network failure like the retained v1.0.4
  resource-envelope attempt. The helper had not been used on a research trace.
- **Disposition:** count such records explicitly as no-response attempts and
  derive their elapsed request interval from the attempt's exact traced start
  and completion timestamps. Keep transport-reported and timestamp-derived
  timing counts separate. Add a focused null-transport case before rerunning
  lint, formatting, compilation, and the test suite.

### LRS-LOCAL-084 — first accounting draft trusted trace-index metadata

- **State:** corrected before commit or trace accounting; no research effect
- **Observation:** a second code review found that the accounting helper bound
  the supplied trace-index file but did not independently prove that the
  current trace still matched every indexed path, size, and hash. A trace
  changed after indexing could therefore have produced accounting over new
  records while citing the older content digest. The helper had not been used
  on any research trace.
- **Disposition:** verify the complete current tree against the index's
  bytewise path order, file count, sizes, individual SHA-256 values, aggregate
  byte count, and record-stream digest; reject symlinks, non-regular files,
  changes observed during hashing, and unsupported algorithms. Add a stale-
  index test, then rerun every focused check.

### LRS-LOCAL-085 — prospective diagnostics lacked two terminal-boundary checks

- **State:** corrected before commit or research-artifact use
- **Observation:** the pre-commit audit found that the calibration comparator
  could read six final-review files without first binding them to the terminal
  calibration-completion record. It also found that both new helpers trusted
  the runbook's outside-trace output path rather than rejecting an output
  placed inside the sealed trace, which would immediately make the index
  stale. No comparator or accounting output existed.
- **Disposition:** require the exact calibration source set, final-review
  relative paths, and SHA-256 values recorded by the terminal completion file.
  Both command-line entry points now reject an output beneath the trace root.
  Add focused nonterminal and in-trace-output cases and rerun every check before
  staging.

### LRS-LOCAL-086 — old-gh CI listing used two unsupported options

- **State:** corrected after the push; no repository or research effect
- **Observation:** after commit `c7bd744` was pushed successfully, the first
  read-only CI listing used the unsupported `--branch` option on this host's
  older GitHub CLI. The next query replaced that option but requested the
  unsupported `workflowName` JSON field. Neither command changed GitHub state.
- **Disposition:** use only fields printed by the installed client's own error
  response and filter the returned records by `headBranch` and `headSha`.
  Workflow `ci`, run `30744720045`, initially reported `in_progress` and later
  completed successfully for exact commit
  `c7bd744bca027f7a4031be9efa8296d68f3ccc11`.

### LRS-LOCAL-087 — outer-label validation used ambiguous jq precedence

- **State:** corrected immediately; no artifact-content or research effect
- **Observation:** the first read-only JSON assertion for the completed
  calibration outer label omitted parentheses around a piped array-length
  check. jq applied `length` to the preceding boolean and exited nonzero before
  the command reached its hash and permission checks. The label file itself was
  valid JSON and was not modified by the failed assertion.
- **Disposition:** parenthesize both boolean operands, rerun the assertion under
  fail-fast behavior, and then record the label's SHA-256 and mode. The corrected
  validation passed; the label is 9,027 bytes, mode 0600, with SHA-256
  `d53c73dc22824b06d06b15865d04bcc254da936b6d883a2642b9a969e66ccb3b`.

### LRS-LOCAL-088 — private-reference scan used an unbounded short token

- **State:** corrected read-only search; no repository or research effect
- **Observation:** the first post-documentation privacy scan searched for the
  three-letter token `arc` without word boundaries. It therefore matched many
  harmless substrings such as “research” and “archive,” producing noisy output
  rather than a useful private-reference check.
- **Disposition:** rerun with case-insensitive word boundaries around each
  prohibited name. The corrected scan returned no match in the tracked study,
  root README, or reciprocal research queue.

### LRS-LOCAL-089 — monitor launch strings conflicted with orchestration parsing

- **State:** corrected before either monitor launched; no workload or research
  effect
- **Observation:** two first attempts to start read-only resource monitors
  embedded shell parameter-expansion syntax in JavaScript template literals.
  The orchestration parser rejected each command before a shell or monitor
  process started.
- **Disposition:** remove the ambiguous shell expansion and relaunch each
  monitor with simpler assignments. Both corrected monitors started normally;
  no experiment, service, trace, or accepted output was touched by the rejected
  calls.

### LRS-LOCAL-090 — workstation health probe unnecessarily used SSH

- **State:** corrected immediately; read-only and no research effect
- **Observation:** an initial workstation health probe tried to SSH to the
  workstation's own hostname because the controlling shell was incorrectly
  treated as a third host. Authentication failed before any remote command ran.
- **Disposition:** verify the controlling hostname first and query local
  systemd, cgroup, memory-pressure, and GPU state directly. The corrected probe
  found both citation scopes active, zero max-limit or OOM events, ample memory
  headroom, and a healthy accelerator temperature.

### LRS-LOCAL-091 — first redacted credential-presence check had invalid quoting

- **State:** corrected before any credential value was printed or used; no
  provider or research effect
- **Observation:** the first shell-only attempt to report whether registered
  provider variables existed mixed nested quote styles in an `awk` expression.
  Bash rejected the command at parse time, before the loop inspected any file.
- **Disposition:** replace the expression with a simpler anchored-name search
  and redact everything after the first equals sign. The corrected read-only
  check found one registered route for each logical external teacher and did
  not expose a credential value.

### LRS-LOCAL-092 — failed-trace helper lookup used the frozen execution checkout

- **State:** corrected read-only lookup; no trace or research effect
- **Observation:** the first attempt to inspect the accounting helper ran from
  the deliberately frozen Qwen execution checkout. That checkout predates the
  helper, so the shell reported three missing script paths and exited before
  reading or writing an artifact.
- **Disposition:** run the already tested helper from the maintenance checkout
  against the absolute immutable trace path. The resulting terminal index and
  accounting files were created outside the indexed tree and verified by hash.

### LRS-LOCAL-093 — v1.0.4 remaining pass exhausted the evidence output ceiling

- **State:** terminal failed trace; prospective v1.0.5 repair registered
- **Observation:** the first Bowman et al. evidence call and its only permitted
  repair both returned HTTP 200 with `finish_reason: length` and exactly 8,192
  completion tokens. The first response ended in malformed JSON; the second
  used its whole allowance in reasoning and returned no final content. The
  runner emitted `qwen_phase_failed` and exited nonzero as designed. No OOM,
  context overflow, grounding failure, accepted Bowman record, or teacher call
  occurred.
- **Disposition:** seal the entire v1.0.4 trace and give it zero remaining-phase
  decision weight. Runtime v1.0.5 changes only the evidence ceiling to 12,288
  tokens. It requires a committed and tagged amendment, focused tests, context-
  headroom audit, fresh lock-held preflight, new trace, and new six-source gate.

### LRS-LOCAL-094 — first v1.0.5 validation command selected incomplete tools

- **State:** corrected before commit or compute; no research effect
- **Observation:** the first focused-check command used the system Python,
  which lacked pytest, and then named a Ruff binary absent from the citation
  environment. Inspection also caught a missing `copy` import in the new test
  before that test ran under the correct environment.
- **Disposition:** add the import, use the registered research-test
  environment for pytest, and use the installed repository linter only with
  the project's configured checks. The corrected focused test completed 19/19;
  no model request or artifact depended on the rejected command.

### LRS-LOCAL-095 — v1.0.5 test initially missed deterministic formatting

- **State:** corrected before commit or compute; no research effect
- **Observation:** scoped lint passed, but Ruff's format check found that the
  newly added configuration-delta test did not match deterministic wrapping.
- **Disposition:** apply Ruff formatting to that test only, then rerun scoped
  lint, formatting, the 19 focused tests, and whitespace validation. All passed.

### LRS-LOCAL-096 — first v1.0.5 draft exceeded the largest packet's context

- **State:** corrected before commit, preflight, server start, or model request
- **Observation:** the first prospective draft doubled the evidence ceiling to
  16,384 tokens. Comparing it with the already recorded 35,644-token maximum
  rendered prompt showed a 52,028-token total, above both the registered 50,000
  minimum and the observed 50,176-token server context.
- **Disposition:** reduce the ceiling to 12,288 tokens. This is 50% above the
  failed allowance, totals 47,932 tokens for the largest frozen request, and
  preserves at least 2,068 tokens of headroom against the registered minimum.
  Rerun the exact live prompt audit before calibration; the 16,384-token draft
  has never been an execution input.

### LRS-LOCAL-097 — first live-context probe conflicted with orchestration parsing

- **State:** corrected before shell execution; no server or research effect
- **Observation:** a tiny lock-held endpoint probe again placed shell default-
  value expansion syntax inside a JavaScript template literal. The orchestration
  parser rejected it before a shell, lock, or HTTP request started.
- **Disposition:** use the already defined runtime-directory variable directly.
  The corrected read-only probe held the experiment lock and confirmed the
  `/apply-template` and `/tokenize` response shapes without generation.

### LRS-LOCAL-098 — context-audit draft selected the wrong workspace ancestor

- **State:** corrected before executing the audit; no research effect
- **Observation:** manual path counting in the preserved audit script initially
  selected the `research/` directory rather than the repository root. Inspection
  caught the off-by-one ancestor before import or endpoint access.
- **Disposition:** correct the ancestor index, run `--help` as an import check,
  then execute the audit under the exclusive lock. All 112 requests tokenized
  and the preserved script is hash-bound with its output.

### LRS-LOCAL-099 — prior context audit reported the upper middle, not the median

- **State:** corrected documentation; no execution or headroom effect
- **Observation:** the first 112-request context report called 14,394 the
  median. The sorted middle values are 14,108 and 14,394, so the ordinary
  even-sample median is 14,251. Minimum, maximum, largest-request identity,
  rendered-prompt hash, and every context-headroom decision were correct.
- **Disposition:** recompute the statistic independently from the new 112-row
  audit, correct the execution record to 14,251, and retain this disclosure.

### LRS-LOCAL-100 — runner identity allowlist omitted frozen runtime v1.0.5

- **State:** contained before trace creation or model request; harness repair
  frozen prospectively
- **Observation:** the first calibration invocation after the successful v1.0.5
  preflights exited with `citation runtime config identity or version differs`.
  The amendment map already bound v1.0.5, but a separate allowlist in `main()`
  still ended at v1.0.4. The requested trace root remained absent.
- **Disposition:** derive supported runtime versions from the amendment map plus
  v1.0.1 and assert the exact set in a focused test. Commit and tag this as
  trace-only harness v1.0.4, then use a new invocation ID and trace root.

### LRS-LOCAL-101 — buffered runner output produced one stale progress report

- **State:** corrected from the append-only event stream; no research effect
- **Observation:** while the fresh v1.0.5 calibration was running, the wrapper's
  terminal output remained buffered. One operator update therefore described
  the first Allman evidence repair as still active after the trace had already
  accepted it and advanced to the second chunk.
- **Disposition:** treat `events.jsonl`, not wrapper stdout, as the authoritative
  live progress source and correct the update immediately. No request, trace
  record, acceptance decision, or model process was changed.

### LRS-LOCAL-102 — first event watcher assumed a scope had a main PID

- **State:** corrected with a path-bound append-only watcher; no research effect
- **Observation:** the first prospective live watcher tried to pass a transient
  systemd scope's empty `MainPID` value to `tail --pid`, which rejected the
  invalid PID before beginning to follow the trace.
- **Disposition:** follow the exact immutable trace's `events.jsonl` path with
  `tail -F` and separately query the exact runner scope for lifecycle state.
  The failed watcher issued no model request and changed no trace content.

### LRS-LOCAL-103 — first calibration-seal command used a stale virtualenv path

- **State:** corrected before either helper ran; no artifact or research effect
- **Observation:** the first post-calibration comparator and private-index
  invocations named a guessed virtualenv path that does not exist on the
  workstation. Both shells exited 127 before Python started, and both requested
  output paths remained absent.
- **Disposition:** verify the helpers are standard-library-only and rerun them
  with the host's explicit `python3` interpreter. Both corrected helpers
  completed successfully, and the failed commands are not represented as model
  or scientific attempts.

### LRS-LOCAL-104 — first Qwen scope probes used the system manager

- **State:** corrected before any process action; no trace or resource effect
- **Observation:** two read-only status probes queried the system service
  manager even though the transient Qwen scopes belong to the user service
  manager. The probes therefore reported inactive units while the authoritative
  event stream and GPU telemetry showed active work.
- **Disposition:** use `systemctl --user` for every Qwen unit query and retain
  the append-only event stream as the progress authority. No process was
  stopped, restarted, or reconfigured because of the incorrect read.

### LRS-LOCAL-105 — combined terminal-documentation patch missed README context

- **State:** rejected atomically; corrected as two exact-context patches
- **Observation:** the first combined patch for the v1.0.5 terminal execution
  record and README summary omitted the preceding word from the README's
  wrapped sentence. The patch tool rejected the entire operation before either
  file changed.
- **Disposition:** apply the execution record and README summary separately
  against their exact current contexts, then run whitespace and content checks.
  The failed patch did not touch the active trace or model process.

### LRS-LOCAL-106 — first parallel documentation-check wrapper had invalid syntax

- **State:** rejected before any nested command; no repository effect
- **Observation:** the first JavaScript wrapper for three independent
  post-documentation checks closed its promise array with the wrong bracket.
  The orchestrator rejected the wrapper before launching any shell.
- **Disposition:** correct the bracket and rerun all three checks; do not count
  the rejected wrapper as a completed validation.

### LRS-LOCAL-107 — generic validator first expected an absent upstream checkout

- **State:** corrected check scope; no protocol or research effect
- **Observation:** the generic protocol validator was first invoked with only
  `--skip-data` in the documentation worktree, which does not contain the
  separate upstream checkout at its default path. It reported that missing
  checkout; repository hygiene and the paper-specific frozen validator passed.
- **Disposition:** rerun the generic structural check with both `--skip-data`
  and `--skip-upstream`, which passed, while retaining the independently
  successful paper-specific validator as the upstream-aware authority.

### LRS-LOCAL-108 — old GitHub client again rejected a branch filter

- **State:** corrected with an exact repository API query; no Git or CI effect
- **Observation:** the first post-push CI lookup used `gh run list --branch`,
  but the installed older GitHub client does not implement that option. It
  printed usage and made no state-changing request.
- **Disposition:** query the exact repository actions endpoint by the pushed
  commit SHA. Do not infer current-branch CI state from an unfiltered run list.

### LRS-LOCAL-109 — read-only packet probe assumed a nonexistent field

- **State:** corrected immediately; no file or experiment effect
- **Observation:** an exploratory `jq` query addressed `source_pages`, while
  the frozen packet stores the content under `source_chunk`. The query failed
  without writing output or contacting a model.
- **Disposition:** inspect the packet schema before constructing ad hoc probes;
  use `source_chunk.extracted_pages` only in the model-facing derived view.

### LRS-LOCAL-110 — v1.0.5 generic repair did not enforce one-line grounding

- **State:** terminal v1.0.5 failure; prospective v1.0.6 repair registered
- **Observation:** the second Gu evidence chunk failed the exact grounding
  validator once, then the generic repair instruction allowed Qwen to join
  three adjacent physical PDF lines on its final permitted attempt. No Gu
  record or remaining-phase completion was accepted.
- **Disposition:** preserve and seal every v1.0.5 attempt at zero weight where
  invalid. Runtime v1.0.6 binds a conservative evidence-only repair prompt,
  permits deletion or a single-line verbatim replacement, and increases only
  evidence calls to three attempts. It requires fresh validation, preflight,
  calibration, and trace; no v1.0.5 output may be copied.

### LRS-LOCAL-111 — final v1.0.5 cgroup counters were not captured

- **State:** irrecoverable reporting limitation; trace content unaffected
- **Observation:** the local model server was stopped after terminal failure
  before its final post-calibration `memory.events` snapshot was copied. The
  calibration-boundary counters were all zero and the continuous guard never
  fired, but exact later counters cannot be reconstructed.
- **Disposition:** disclose the missing counters and do not infer zeros. Future
  terminal wrappers must copy cgroup counters before stopping the model route.

### LRS-LOCAL-112 — terminal server poll requested excessive buffered output

- **State:** operational only; authoritative server log unaffected
- **Observation:** a final interactive-session poll returned enough buffered
  llama-server stdout to exceed the tool display budget, so the display was
  truncated. The server's append-only on-disk log and research trace remained
  intact.
- **Disposition:** poll bounded event tails or the on-disk log rather than a
  long-lived server session's full buffered stream.

### LRS-LOCAL-113 — first v1.0.6 format check found three unformatted files

- **State:** corrected before commit, tag, preflight, or model request
- **Observation:** focused lint and tests passed, but Ruff's check-only formatter
  reported the runner, preflight, and focused-test files would be reformatted.
- **Disposition:** apply the deterministic formatter, then repeat lint,
  format-check, compilation, and focused tests before freezing v1.0.6.

### LRS-LOCAL-114 — generic validator was given an unsupported paper switch

- **State:** corrected before commit, tag, preflight, or model request
- **Observation:** after the paper-specific validator passed, the first generic
  validator invocation supplied `--paper 2607.17674`. That script has no such
  option and exited after printing usage without performing validation.
- **Disposition:** use the generic validator's own documented arguments and
  retain the paper-specific validator as the study authority.

### LRS-LOCAL-115 — generic validator initially included unavailable datasets

- **State:** expected local-tree limitation; corrected scoped check passed
- **Observation:** the next generic validation command omitted `--skip-data` and
  therefore reported the intentionally absent upstream dataset release in this
  checkout. It found no new protocol defect.
- **Disposition:** rerun with both `--skip-data` and `--skip-upstream`, as already
  required by LRS-LOCAL-107; do not represent that scoped check as validating
  files that are absent locally.

### LRS-LOCAL-116 — full suite repeated the known ignored-fixture limitation

- **State:** isolated; no effect on this study
- **Observation:** the v1.0.6 repository-wide test run passed 181 tests and
  repeated LRS-LOCAL-034/LRS-LOCAL-059 on the different study's ignored
  `paper_repro/SLM-RL-Agents/results/all_results.json`. The current CI workflow
  reconstructs that pinned upstream tree before running the suite.
- **Disposition:** do not copy a private or unrelated result into this checkout.
  Retain the local 181-pass/one-environment-failure record, rely on the 21
  focused v1.0.6 tests and scoped validators locally, and require the normal
  GitHub workflow to pass after push.

### LRS-LOCAL-117 — long-lived server poll exceeded the display budget

- **State:** corrected operational practice; append-only server log unaffected
- **Observation:** a second interactive poll of the long-lived llama-server
  session returned more buffered output than the tool display budget.
- **Disposition:** use bounded on-disk tails and `/slots`; never treat truncated
  terminal display as loss of the authoritative server log.

### LRS-LOCAL-118 — first private v1.0.6 context helper failed style checks

- **State:** corrected before any audit request
- **Observation:** Ruff found unsorted imports in the private context-audit
  helper.
- **Disposition:** format and lint generated diagnostic code before execution;
  retain the corrected helper and its manifest.

### LRS-LOCAL-119 — remote read-only probe assumed `rg` was installed

- **State:** corrected; no experiment effect
- **Observation:** one dev-box inspection exited 127 because that host lacks
  `rg`.
- **Disposition:** use the available bounded `grep`/`find` tools on that host.

### LRS-LOCAL-120 — first accepted-line diagnostic needed formatting

- **State:** corrected before producing a diagnostic result
- **Observation:** the private v1.0.5 accepted-line audit helper initially had
  import-order and formatting errors.
- **Disposition:** apply deterministic formatting, repeat checks, then manifest
  the corrected diagnostic tree.

### LRS-LOCAL-121 — combined diagnostic and hash output was truncated

- **State:** corrected by bounded commands; artifacts unaffected
- **Observation:** one combined read-only accepted-line check and hash dump
  exceeded the tool-output budget.
- **Disposition:** run bounded diagnostics and hash reports separately.

### LRS-LOCAL-122 — guard heartbeat poll accumulated excessive output

- **State:** corrected by shorter deltas; guard remained active
- **Observation:** a Qwen-guard poll accumulated enough heartbeat lines to
  truncate the display.
- **Disposition:** poll frequent, bounded deltas; the guard log remains the
  complete source.

### LRS-LOCAL-123 — exploratory probes used several wrong paths or fields

- **State:** corrected; all were read-only precondition failures
- **Observation:** exploratory commands used a wrong diagnostic filename, an
  incomplete trace-index filename, incorrect JSON fields, one malformed `jq`
  quote, and a venv interpreter for a globally installed Ruff executable.
- **Disposition:** inspect exact paths and schemas first, then repeat with the
  correct executable. None changed a trace or contacted a model.

### LRS-LOCAL-124 — first remaining launch used the wrong Python runtime

- **State:** rejected before an event or request; corrected
- **Observation:** the first v1.0.6 remaining-phase launch used the repository
  Python 3.12 venv instead of the calibration-bound system Python 3.10. Stable
  input equality failed closed.
- **Disposition:** relaunch with `/usr/bin/python3`; preserve the rejection as a
  no-call local error.

### LRS-LOCAL-125 — instruction-file search crossed too broad a tree

- **State:** interrupted; no file or experiment effect
- **Observation:** `find .. -name AGENTS.md` crossed an unnecessarily large
  parent tree and did not return promptly.
- **Disposition:** inspect only the repository and direct instruction-bearing
  ancestors.

### LRS-LOCAL-126 — first Windows process probes used bad path and quoting

- **State:** corrected; both failed read-only
- **Observation:** the first probe used an unavailable `powershell.exe` path;
  the next allowed Bash to expand PowerShell `$` expressions.
- **Disposition:** use the explicit Windows PowerShell path and single-quoted
  PowerShell source. Neither attempt signaled a process.

### LRS-LOCAL-127 — WSL-only process check missed a Windows GPU workload

- **State:** corrected before any process action
- **Observation:** `pgrep` inside WSL led to the incorrect statement that no
  local interactive Windows GPU workload was active. Windows GPU counters and
  `Get-Process` showed that it was responsive.
- **Disposition:** inspect Windows processes through Windows APIs before making
  cross-OS resource claims. The unrelated process was never signaled or
  reconfigured.

### LRS-LOCAL-128 — one slot query used the wrong loopback port

- **State:** corrected; no server effect
- **Observation:** a read-only `/slots` query used port 8091 although the frozen
  route was port 8080 and received connection refused.
- **Disposition:** derive the port from the bound route before diagnostics.

### LRS-LOCAL-129 — two parallel status helpers had a JavaScript syntax error

- **State:** corrected; nested commands did not run
- **Observation:** two ad hoc parallel poll wrappers omitted a closing
  parenthesis and failed during parsing.
- **Disposition:** use explicit named promises for multi-session polls.

### LRS-LOCAL-130 — completed server-session poll returned 67,035 tokens

- **State:** display-only truncation; on-disk log intact
- **Observation:** polling a completed llama-server terminal session returned
  its full buffered history and far exceeded the requested display budget.
- **Disposition:** never poll that session again; use the hash-bound log file.

### LRS-LOCAL-131 — v1.0.6 bound a process-random media marker

- **State:** terminal local harness defect; prospective v1.0.7 fix registered
- **Observation:** llama.cpp randomizes text-only `/props.media_marker` on each
  process. v1.0.6 included it in stable run-input equality, so a scientifically
  identical restart failed before an event or model request. A restart with
  `LLAMA_MEDIA_MARKER` pinned to the immutable original proved it was the sole
  difference.
- **Disposition:** never edit the v1.0.6 input. Runtime v1.0.7 removes exactly
  this nonce from equality, records each observed value, and retains strict
  comparison for every other field. Start a fresh trace.

### LRS-LOCAL-132 — workload-coexistence diagnostic consumed an attempt slot

- **State:** terminal v1.0.6 operator stop; no citation weight
- **Observation:** after exact marker pinning, the operator resumed while the
  responsive, unrelated Windows GPU workload was still active. Prompt
  evaluation slowed from seconds to more than one minute per 2,048-token batch. The runner
  was stopped before its first model event or timeout, but the immutable
  `attempt-02` directory had already been created.
- **Disposition:** retain both incomplete calls and their bounded 734.054536
  seconds separately from completed-call accounting. Do not remove a retry
  directory. Fresh v1.0.7 work waits for natural GPU availability.

### LRS-LOCAL-133 — first operator-stop events were inserted before later events

- **State:** corrected before the final trace seal; superseded indexes retained
  privately
- **Observation:** the first manual terminal-event patch matched an older line
  rather than end-of-file, placing the stop before events already appended by a
  resume. The first accounting attempt therefore rejected a nonterminal phase,
  and two preliminary indexes became stale.
- **Disposition:** use journal timestamps to reconstruct the two operator-stop
  boundaries, correct the still-unreleased event order, disclose this repair,
  and designate only the final index ending `operator-stop-final.json` as
  authoritative.

### LRS-LOCAL-134 — one error-ledger probe used the repository root

- **State:** corrected; read-only
- **Observation:** a status command tried `ERROR_LOG.md` at repository root
  instead of the study-local path and returned file-not-found.
- **Disposition:** use `research/replications/2607.17674/ERROR_LOG.md`.

### LRS-LOCAL-135 — active-server metrics probe timed out

- **State:** diagnostic-only; no request or server change
- **Observation:** one five-second `/metrics` read timed out while a heavily
  contended model request occupied the single llama.cpp slot.
- **Disposition:** use `/slots`, bounded log tails, and process telemetry; a
  diagnostic timeout is not a model or paper failure.

### LRS-LOCAL-136 — first v1.0.7 format check found three files

- **State:** corrected before commit, tag, preflight, or model request
- **Observation:** lint, compilation, and 35 focused tests passed, but Ruff's
  check-only formatter identified three edited Python files.
- **Disposition:** apply deterministic formatting and repeat all focused checks;
  the repeated suite passed 36 tests after the additional source-binding test.

### LRS-LOCAL-137 — full v1.0.7 suite repeated the known ignored fixture

- **State:** isolated; no effect on this study
- **Observation:** the repository-wide run passed 189 tests and repeated the
  one known different-study failure because ignored
  `paper_repro/SLM-RL-Agents/results/all_results.json` is absent locally.
- **Disposition:** do not manufacture or copy that unrelated result. Require
  the GitHub workflow to reconstruct its pinned upstream fixture and pass, while
  retaining the 36 focused passes and both scoped validator passes locally.

### LRS-LOCAL-138 — first v1.0.7 push targeted the upstream remote

- **State:** corrected immediately; unintended refs removed
- **Observation:** the operator pushed the new branch and tag to Git remote
  `origin`, which is the paper-reproduction repository, instead of the existing
  NULSPEC collaboration remote. No pull request or release was created there.
- **Disposition:** delete only the just-created upstream branch and tag, verify
  both deletions, then push the unchanged commit and tag to `nulspec`. Use the
  branch's configured upstream rather than assuming the remote named `origin`.

### LRS-LOCAL-139 — first post-push PR query used unsupported metadata

- **State:** corrected; read-only GitHub queries only
- **Observation:** the installed older `gh` client rejected `headRefOid`, and a
  follow-up exact-run API query used an incorrectly transcribed full commit SHA.
- **Disposition:** use only fields listed by this client and obtain the head SHA
  verbatim from `git rev-parse`. The corrected PR query showed both checks in
  progress on draft PR 26.

### LRS-LOCAL-140 — v1.0.7 draft reintroduced a private workload name

- **State:** corrected before preflight or any v1.0.7 model request
- **Observation:** the first tracked v1.0.7 wording named an unrelated personal
  workload despite the prior decision to keep personal operations out of the
  research draft.
- **Disposition:** retain exact details only in the ignored private trace, use
  neutral resource-contention language in tracked research records, and replace
  the prospective runtime tag before any execution. Scientific settings and
  trace findings are unchanged. The deleted provisional tag object
  `8b3cc34031cd651f5014341ae030b620f6e393b9` pointed to `09e8250`; replacement
  tag object `7cb819465dff12f3e242bc6b1beed969f3968619` points to corrected commit
  `f9a78ce4dc0608e45170f5fa295a688341598ed8`.

## External acquisition limitations

### LRS-EXTERNAL-001 — Hugging Face paper Markdown returned 404

- **State:** bypassed; no scientific effect
- **Observation:** Hugging Face's paper API returned metadata for 2607.17674,
  but its corresponding `.md` endpoint returned HTTP 404.
- **Disposition:** used the canonical arXiv v1 PDF and source archive.

### LRS-EXTERNAL-002 — automated OpenReview PDF routes returned 403

- **State:** bypassed with identity-matched archive copies
- **Observation:** four cited OpenReview landing pages were public, but their
  PDF and attachment routes returned a browser-verification HTTP 403 to the
  bounded acquisition client.
- **Disposition:** use pre-target-paper Internet Archive captures of the exact
  canonical OpenReview PDF URLs. Record both the cited URL and archival route;
  do not treat the archive as a different scholarly source.

### LRS-EXTERNAL-003 — two legacy NeurIPS links returned 404

- **State:** bypassed with canonical proceedings PDFs
- **Observation:** the bibliography's short `papers.nips.cc/paper/{id}` URLs
  for InfoGAN and the conditional VAE paper now return HTTP 404.
- **Disposition:** use the matching title/author PDFs on the official NeurIPS
  proceedings host and retain the failed cited URLs in the acquisition trace.

### LRS-EXTERNAL-004 — Springer landing page exposed no retrievable PDF

- **State:** bypassed with the matching author preprint
- **Observation:** the DOI landing page for the concept-bottleneck chapter was
  accessible but exposed no PDF link to the acquisition client.
- **Disposition:** use arXiv:2311.05014, whose title and author list match the
  cited chapter, and record the substitution rather than scraping a paywall.

### LRS-EXTERNAL-005 — two DOI routes downgrade HTTPS and live PDFs are guarded

- **State:** bypassed with identity-matched archive copies
- **Observation:** the Teicher and Yakowitz DOI resolvers redirect from HTTPS
  to legacy HTTP Project Euclid URLs. Their manually upgraded HTTPS routes
  return verification pages rather than PDFs to the acquisition client.
- **Disposition:** retain the failed DOI traces and use archived Project Euclid
  PDFs whose bibliographic identities match the cited articles. The later
  Yakowitz archive capture postdates the target submission, which is disclosed;
  it contains the immutable 1968 source article rather than a later substitute.

### LRS-EXTERNAL-006 — Project Euclid verification behavior was intermittent

- **State:** bypassed with identity-matched archive copies
- **Observation:** the first two acquisition attempts retrieved the Allman and
  Jiang PDFs from Project Euclid, but the third clean attempt received HTML
  verification pages from the same canonical PDF URLs. This made an otherwise
  identical full-source acquisition nondeterministic.
- **Disposition:** preserve all attempts and pin pre-submission Internet Archive
  captures of the exact Project Euclid PDF URLs for a self-contained fresh
  acquisition. Do not combine files opportunistically across attempts.

## Upstream/release limitations

### LRS-UPSTREAM-001 — paper and released response source differ

- **State:** open; interpretation-relevant
- **Observation:** the manuscript specifies model-sampled responses while the
  released paper config specifies benchmark responses.
- **Disposition:** freeze separate R and M tracks; never silently substitute.

### LRS-UPSTREAM-002 — reported result artifacts are absent

- **State:** open; limits exact numerical comparison
- **Observation:** no raw results, checkpoints, numerical tables, or plotting
  code are released.
- **Disposition:** preserve digitized Figure 3 values and label their precision.

### LRS-UPSTREAM-003 — complete reported configuration grid is absent

- **State:** open; blocks exact full-figure reconstruction
- **Observation:** the release does not specify every pretrained method arm or
  the 504-run random-initialization grid. The README explicitly describes its
  configs as starting points.
- **Disposition:** execute only preregisterable arms in v1.0.0; seek author
  clarification before a figure-reconstruction amendment.

### LRS-UPSTREAM-004 — ELBO versus beta-ELBO mapping is ambiguous

- **State:** open; blocks exact baseline registration
- **Observation:** Figure 3 plots both labels, but the paper/release does not
  provide an unambiguous selection rule and exact beta/schedule for each.
- **Disposition:** do not infer the mapping post hoc.

### LRS-UPSTREAM-005 — training variance is not reported

- **State:** open; limits generalization
- **Observation:** one seed is disclosed, task points are plotted, and no
  fresh-training or fresh-decoding variability is reported.
- **Disposition:** primary inference is conditional on the disclosed seed;
  additional seeds are a separately labeled extension.

### LRS-UPSTREAM-006 — documented outputs are not ignored

- **State:** open; minor reproducibility friction
- **Observation:** the pinned repository does not ignore its documented
  `.data/` and `.runs/` outputs or Python bytecode caches, so following the
  README makes a clean checkout appear dirty.
- **Disposition:** permit only those exact generated path classes in our source
  cleanliness check; continue hashing the tracked Git archive independently.

### LRS-UPSTREAM-007 — released attention path is not bitwise deterministic

- **State:** open; limits exact rerun reproducibility
- **Observation:** the unmodified pinned training stack warns that PyTorch's
  memory-efficient scaled-dot-product attention uses a nondeterministic
  algorithm. The disclosed random seed therefore does not, by itself,
  guarantee bit-identical checkpoints or metrics across reruns.
- **Disposition:** preserve the warning and the released implementation for the
  preregistered primary run. Treat exact-run comparisons as seed-conditional,
  record complete environment and artifact hashes, and evaluate fresh-run
  variability only in a separately labeled extension.

### LRS-UPSTREAM-008 — evaluator discards per-example metric outcomes

- **State:** open; blocks the registered conditional bootstrap
- **Observation:** the released evaluator writes only aggregate Distributional
  Fidelity and Analogical Consistency scalars. It does not retain the 10,000
  fidelity-generation outcomes or the 1,024 analogical-pair outcomes needed to
  audit individual classifications or bootstrap within-evaluation uncertainty.
- **Disposition:** preserve the exact aggregate-only evaluator in primary
  runs. Report the registered interval as unavailable, not zero-width; any
  record-preserving rerun requires a separately labeled instrumentation
  extension and cannot replace the primary observation.

### LRS-UPSTREAM-009 — reconstruction includes the latent closing delimiter

- **State:** open; interpretation-relevant implementation/method difference
- **Observation:** the manuscript reconstruction sum is over response tokens,
  but the released conditioned-record builder starts supervision at `</z>`, one
  token before its declared response span. The frozen-base directed weight is
  zero at that extra position, while the uniform component still trains it;
  ELBO and global-scale variants weight it uniformly in full. The extra active
  position also changes the denominator inside the uniform average and
  `kappa`'s base loss from `T_y` to `T_y + 1`, while `c_theta` remains estimated
  over `T_y`. Across the frozen training split, the resulting mean structural
  scale ratio is 0.967978 (response lengths 12--121, median 32).
- **Disposition:** preserve this behavior in every released-code primary arm.
  Run a response-span-only mask as a separately labeled paired extension and
  report whether it changes the conclusion.

### LRS-UPSTREAM-010 — fidelity batches restart one sampling stream

- **State:** open; affects Monte Carlo dependence and uncertainty
- **Observation:** standalone Distributional Fidelity evaluation passes the
  same seed to every generation batch, and the generation helper manually
  reseeds at the start of each call. Corresponding rows and token positions in
  successive batches therefore reuse random draws instead of advancing one
  stream through all 10,000 prompts.
- **Disposition:** preserve the released evaluator for the primary scalar and
  do not apply an independent-example interval to it. Compare against an
  advancing-RNG, record-preserving evaluation as a labeled sensitivity.

### LRS-UPSTREAM-011 — ambiguous analogical matches use set intersection

- **State:** open; potentially affects a subset of pair outcomes
- **Observation:** the manuscript expresses Analogical Consistency as equality
  of inferred strategies. The released evaluator represents compatible
  strategies as sets and counts a success whenever the two sets overlap.
- **Disposition:** retain the released rule for the primary. In a
  record-preserving extension, report ambiguous-pair prevalence and recompute
  under literal set equality and unique-only conventions.

### LRS-UPSTREAM-012 — Track M response batches also restart one sampling stream

- **State:** open; affects manuscript-method sampling dependence
- **Observation:** base-model response construction invokes the shared
  generation helper separately for each batch with one unchanged seed. The
  helper reseeds on every call, and the train, validation, and test loops reuse
  the same configuration. Corresponding rows across batches and splits
  therefore share underlying random draws rather than advancing an independent
  stream through the 120,000 prompts.
- **Disposition:** preserve the released behavior in primary Track M so it is
  code-reproducible. Treat monotonically advanced, record-preserving response
  sampling as a paired extension and report whether it changes results.

### LRS-UPSTREAM-013 — executable arms have no reported hardware requirement

- **State:** open; reproducibility-planning limitation
- **Observation:** neither the manuscript nor the pinned repository reports the
  accelerator model or per-arm device-memory requirement. In our unchanged
  environment, even the Qwen2.5-0.5B manuscript-method arm exceeded an RTX
  4090's 24 GB during pretraining `c_theta` estimation after response sampling.
- **Disposition:** report the observed failure and successful hardware envelope
  without implying that 24 GB was claimed to be sufficient. Ask the authors
  which hardware and peak-memory envelope produced the reported runs, and add
  measured peak device memory from an eligible 96 GB retry.

### LRS-LOCAL-141 — one local status probe assumed a Windows bridge binary

- **State:** corrected read-only diagnostic; no experiment effect
- **Observation:** a combined status command invoked `powershell.exe` from a
  Linux execution context where that bridge was unavailable and returned 127
  after the GPU query had already succeeded.
- **Disposition:** keep workstation-specific process checks on the workstation
  connection and do not infer process state from that failed subcommand.

### LRS-LOCAL-142 — observer output transport propagated SIGPIPE to R-1.5B evaluation

- **State:** failed primary attempt preserved; runtime correction and narrowly
  labeled evaluator recovery registered
- **Observation:** Track R Qwen2.5-1.5B completed all 782 factorization batches,
  wrote the final checkpoint, and recorded final sampled-test fidelity 0.9750.
  The separate released evaluator then began loading that checkpoint while its
  progress output passed through nested `tee` processes to a bounded SSH
  observer stream. The attempt ended with code 141 and wrote
  `run.failed.json` SHA-256
  `ad42225ff31b341779f3e6c6affd577b2a82d39a89e0a097459325881ee4fb82`.
  The scope journal reports a 12.0 GiB memory peak and no kernel OOM; there was
  no CUDA exception, Xid, thermal trip, or protected-service restart. The
  truncated evaluation output and lack of a Python traceback are consistent
  with SIGPIPE from the observer chain, not a scientific-code failure.
- **Disposition:** never count the failed attempt as an uninterrupted complete
  run and never rewrite its terminal evidence. Primary runner output now goes
  directly to a regular file. Runtime amendment v1.0.1 permits only the
  authors' unchanged standalone evaluator to be rerun from the hashed final
  checkpoint, with separate recovery manifests and an explicit
  `completed_recovered_evaluation` label.

### LRS-LOCAL-143 — one parallel tool wrapper referenced an undeclared variable

- **State:** corrected orchestration helper; no experiment effect
- **Observation:** after three awaited read-only/plan calls completed, the
  JavaScript wrapper assigned their results to undeclared `polled` and raised a
  `ReferenceError`, suppressing the wrapper's displayed output.
- **Disposition:** reran only the missing read-only displays with a declared
  constant. The already-completed plan update was not duplicated as compute.

### LRS-LOCAL-144 — one completed-evaluator probe requested a carriage-return-heavy log

- **State:** corrected read-only diagnostic; no experiment effect
- **Observation:** printing the full prior 0.5B evaluator log expanded progress
  updates into 41,081 tokens and caused tool-output truncation. The underlying
  artifact was neither changed nor truncated.
- **Disposition:** use file timestamps, metrics JSON, and narrowly filtered log
  tails for future timing checks.

### LRS-LOCAL-145 — the remote host lacks ripgrep

- **State:** corrected read-only diagnostic; no experiment effect
- **Observation:** a source lookup correctly tried `rg` first, but the remote
  research host does not provide it and returned 127.
- **Disposition:** used the available `grep` fallback for that remote checkout;
  no source or environment package was changed.

### LRS-LOCAL-146 — first recovery guard used a pipefail-unsafe emptiness probe

- **State:** corrected before commit, deployment, or recovery execution
- **Observation:** the initial recovery draft checked a directory with
  `find -print -quit | grep -q`. Under `set -o pipefail`, an early reader exit
  can make a correct nonempty result appear as SIGPIPE.
- **Disposition:** replaced the pipeline with a bounded command substitution
  before any recovery was launched and added transport-focused tests.

### LRS-LOCAL-147 — first recovery validation used the wrong Ruff environment

- **State:** corrected before commit or deployment
- **Observation:** the repository test virtual environment provides pytest but
  not Ruff. Two validation commands therefore returned "No module named ruff";
  because that composite shell did not enable fail-fast behavior, the later
  passing pytest command became the composite exit status.
- **Disposition:** treated the composite call as failed, invoked the installed
  pinned Ruff executable directly, and kept lint, format, and pytest results as
  independently checked gates.

### LRS-LOCAL-148 — first recovery format gate found three files

- **State:** corrected before commit or deployment
- **Observation:** Ruff's check passed, while its format check identified the
  analyzer and two new/updated tests.
- **Disposition:** applied the deterministic formatter and reran lint, format,
  and the focused seven-test suite successfully.

### LRS-LOCAL-149 — full suite repeated the known unavailable external fixture

- **State:** known unrelated fixture absence; focused recovery tests pass
- **Observation:** despite the existing LRS-LOCAL-137 record, the recovery
  validation reran the full local suite. It again found only the untracked
  `paper_repro/SLM-RL-Agents/results/all_results.json` fixture unavailable:
  193 tests passed and that one test failed before reading any payload.
- **Disposition:** do not weaken or skip the test in tracked code. Report the
  full-suite limitation separately from the seven passing recovery-focused
  tests and rely on CI's provisioned fixture for the repository-wide gate.
