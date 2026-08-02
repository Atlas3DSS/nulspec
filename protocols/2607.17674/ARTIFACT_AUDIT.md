# Public artifact audit: arXiv:2607.17674v1

## Available and pinned

- arXiv abstract, PDF, and TeX source for v1;
- MIT-licensed upstream repository at commit
  `0c0f221d7dc37cd4eb7fb1af3332520bccf4d9fe`;
- frozen `uv.lock` and executable small-CPU example;
- full benchmark generator and paper benchmark config;
- Qwen2.5 0.5B and 1.5B base-adaptation configs;
- one global-plus-token factorization config and one evaluation config;
- objective parameter mapping for five named objectives;
- benchmark parsers and per-strategy validators.

The upstream repository has one public commit, no release tag, and no release
branch that supplies an alternative recipe. Its clean Git archive digest is
recorded in `SOURCE_MANIFEST.json`.

The repository does not ignore its documented `.data/` and `.runs/` outputs or
Python bytecode caches. Running the documented example therefore makes an
otherwise unchanged checkout appear dirty. Our validator permits only those
known generated paths while continuing to reject every tracked modification or
unexpected untracked path.

## Missing from the public release

- raw experiment results or per-example records;
- trained base-model or factorization checkpoints;
- exact numerical values behind the paper figures;
- figure-generation and run-selection code;
- exact pretrained beta and schedule chosen for every Figure 3 method;
- a definition that unambiguously separates the plotted `ELBO` and
  `beta-ELBO` categories;
- the architecture and executable config registry for the reported 504-run
  random-initialization grid;
- independent training seeds or run-to-run uncertainty.

These gaps prevent exact end-to-end reconstruction of every paper figure from
public artifacts alone. They do not prevent execution of the four primary arms
registered in protocol v1.0.0.

## Manuscript/release conflict

The manuscript's experiment section, method section, training algorithm, and
appendix objective table say factorization is trained on responses sampled
from the frozen fitted model. The released `configs/paper/factorization.json`
uses benchmark responses. The README acknowledges both paths and argues that
they are approximately equal after near-zero-loss base fitting.

Because approximate equality is itself testable, it is not assumed. The
released and manuscript paths are separate tracks.

## Reported-value extraction

Figure 3 was rendered directly from the arXiv v1 source asset. Bar heights were
digitized against its 0--1 y-axis to approximately 0.01 precision. No numerical
labels were embedded in the source PDF. The digitizations are reference values,
not recovered author data.

## Citation inventory

The bibliography contains 45 entries and the manuscript cites 41 unique keys.
A claim-level citation audit is registered but has not begun. Its source PDFs,
local-review traces, teacher scores, and outer adjudication will remain separate
from the primary experimental observations.
