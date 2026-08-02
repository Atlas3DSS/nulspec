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

## External acquisition limitations

### LRS-EXTERNAL-001 — Hugging Face paper Markdown returned 404

- **State:** bypassed; no scientific effect
- **Observation:** Hugging Face's paper API returned metadata for 2607.17674,
  but its corresponding `.md` endpoint returned HTTP 404.
- **Disposition:** used the canonical arXiv v1 PDF and source archive.

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
