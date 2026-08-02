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
