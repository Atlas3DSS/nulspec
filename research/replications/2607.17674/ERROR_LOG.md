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

### LRS-LOCAL-013 — relative DOI redirects were validated before resolution

- **State:** corrected; no scientific effect
- **Observation:** the first citation-acquisition attempt rejected relative
  redirect targets returned by two Project Euclid DOI routes because the safety
  check ran before joining them to the public HTTPS origin.
- **Disposition:** preserve the incomplete attempt, resolve redirects against
  their requesting HTTPS URL before applying the same public-host validation,
  and issue a fresh acquisition attempt.

### LRS-LOCAL-014 — ad hoc archive query did not isolate per-item timeouts

- **State:** corrected; no scientific effect
- **Observation:** a read-only query for four Internet Archive capture records
  timed out on its third item and stopped before querying the fourth.
- **Disposition:** retained the partial output and queried the two remaining
  identifiers separately with bounded retries. No acquisition record or source
  selection was overwritten.

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
