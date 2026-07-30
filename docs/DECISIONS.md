# Decision log

## D001 — Reproduction precedes extension

**Status:** accepted, 2026-07-30

Primary reproduction results are frozen before corrections, external judges,
or new hypotheses are evaluated. This prevents an extension from being
mistaken for evidence about the released method.

## D002 — Conflicting sources remain separate tracks

**Status:** accepted, 2026-07-30

The paper, README, and launch scripts for arXiv:2607.25091 contain incompatible
settings. The project will not synthesize an undocumented “best guess.” It
defines a manuscript track and a released-code track, with every conflict
listed in the protocol.

## D003 — Existing two-arm evidence is immutable pilot work

**Status:** accepted, 2026-07-30

The completed Pythia-70M/TinyStories and Pythia-410M/TinyStories runs are
retained with their original labels and paths. They inform feasibility and
audit design but do not substitute for the preregistered full matrix.

## D004 — GitHub is the source of truth

**Status:** accepted, 2026-07-30

Code, protocol versions, decisions, issues, and reports are reviewed through
GitHub. Large model/data artifacts remain external and are bound to Git
revisions through hash manifests.

## D005 — Protect unrelated production workloads

**Status:** accepted, 2026-07-30

The Palworld server is out of experimental scope. Dev-box jobs must use explicit
GPU identity checks and CPU, RAM, process, I/O, and concurrency limits. A run
must stop rather than relax these limits automatically.
