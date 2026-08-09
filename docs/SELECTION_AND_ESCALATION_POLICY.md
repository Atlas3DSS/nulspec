# NULSPEC selection and escalation policy

- Policy version: `1.0.0`
- Effective: `2026-08-09T15:42:50Z`
- Scope: prospective replication starts authorized after the effective time

This policy is designed to make a sequence of replications interpretable as a
corpus rather than only as individually documented case studies. It does not
retroactively relabel NULSPEC's first intake as systematic or randomized. The
public selection ledger identifies those candidates as
`pre-policy-convenience-v1`.

## Near-term program boundary

NULSPEC currently replicates empirical claims in computational machine
learning. Cross-domain expansion is deferred until the ML program has a mature
uniform corpus, stable selection and escalation procedures, and the relevant
domain expertise. Original NULSPEC experiments and extensions occupy a
separate lane and never count toward the external-replication quota.

## Intake record

Every paper considered must enter the append-only public selection ledger,
including papers that are deferred or rejected. An intake record contains:

- the external paper identifier and primary claim scope;
- the selection state and method;
- why it was considered, selected, deferred, or rejected;
- estimated minimum, likely, and maximum GPU-hours;
- estimated human-hours;
- exact, compatible, or infeasible replication classification with rationale;
- protocol, artifact, audit, human-approval, publication, and quota state; and
- actual cost, or an explicit `not_started`, `in_progress`, or `audit_pending`
  state until final accounting is available.

Estimates never substitute for actual cost. Corrections append or version the
record; they do not erase the previous selection decision.

## Objective eligibility rules

A candidate is eligible only when all of the following are true:

1. It contains an empirical claim published outside NULSPEC.
2. At least one primary claim maps to a measurable endpoint and a verdict rule
   that can be frozen before full execution.
3. Public evidence supports an exact reproduction or an explicitly bounded
   compatible reproduction.
4. The smallest claim-complete design fits a declared hardware, GPU-hour,
   human-hour, storage, and safety envelope.
5. The work falls within computational ML and the expertise currently
   available to the program.
6. Confirming, contradictory, null, failed, and inconclusive outcomes are all
   acceptable before selection.

Code release is evidence, not an automatic eligibility requirement. A
manuscript-only reconstruction can remain eligible when its assumptions and
deviations can be bounded. Missing artifacts can instead make a proposed exact
stage infeasible; that decision and the audit supporting it stay public.

## Selection blocks

Replication starts are allocated in prospective blocks of three:

- two priority slots may be selected for scientific value, cost, timeliness,
  corpus balance, or operational fit; and
- at least one slot is a reproducible random draw from every eligible,
  not-yet-started candidate that fits the declared compute band for that slot.

Votes and nominations measure interest. They do not determine eligibility,
protocols, analysis, or verdicts.

### Reproducible random draw

Before randomness is obtained, NULSPEC publishes the ordered eligible pool,
the compute band, the policy version, and a SHA-256 manifest of those inputs.
The pool is sorted by paper identifier. NULSPEC then obtains the first public
randomness value timestamped after the pool freeze and computes:

```text
digest = SHA-256(pool_manifest_sha256 + ":" + randomness_value)
selected_index = unsigned_integer(digest) modulo pool_size
```

The pool, source and value of randomness, digest, index, and selected paper are
published. If later evidence makes the selected paper infeasible, that paper
remains recorded. A replacement is a separate declared draw derived from the
same frozen inputs and an incrementing counter; there are no silent redraws.

## Staged replication and power escalation

### Stage 1 — claim-complete first pass

Run the cheapest design that covers the frozen primary claim matrix. Match the
paper's repetitions when feasible, but do not spend uniformly on extra seeds
that cannot affect the conclusion. A one-realization result may establish code
path behavior; by itself it does not estimate training-to-training or
decoding-to-decoding variability.

### Automatic escalation trigger

Before interpreting a material disagreement as evidence against the published
claim, escalate when all of these conditions hold:

1. The first pass reverses a headline direction, crosses a predeclared
   materiality or equivalence boundary, or otherwise changes the paper-level
   conclusion.
2. Training, sampling, decoding, data order, or another stochastic source could
   plausibly explain the disagreement.
3. Additional independent repetitions are feasible within a declared maximum
   budget.

### Stage 2 — fresh independent repetitions

Freeze a separate escalation protocol before launching more compute. It names
the disputed conditions, estimand, independent seed or repetition unit,
uncertainty method, materiality or equivalence boundary, stopping rule, and
maximum budget. Use at least three fresh independent repetitions per disputed
condition, or the paper's larger declared count. Additional repetitions may be
added only under that frozen stopping rule; favorable optional stopping is not
allowed.

If the maximum budget is reached without resolving the relevant uncertainty,
the result remains limited or inconclusive. Disclosure of low power does not
turn a one-seed disagreement into a non-replication verdict.

## Automated audit boundary

Model outputs are automated release consistency audits. They check packet
integrity, internal consistency, required fields, trace bindings, and obvious
scope errors. They have zero scientific decision weight and are not presented
as peer review, independent domain expertise, or additional replications.

A model audit can keep a release blocked for human inspection. It cannot make a
scientific result more valid. Publication requires a distinct human decision on
the immutable release packet, and author communication requires separate human
approval.

## The NULSPEC 20 corpus

A paper counts toward the first 20 only after an externally published claim has
completed the same end-to-end process: registered scope, frozen protocol,
terminal artifacts, analysis, automated consistency audit, human publication
approval, and public release. Interesting original research, benchmark
extensions, internal tooling, and unfinished attempts do not count.

Each completed record uses a common set of fields so the corpus can eventually
support analysis of code availability, dependency locking, venue, paper age,
hardware changes, evaluation design, final cost, and replication outcome. Any
cross-study reliability claim must state the selection policy and distinguish
priority-selected, randomized, and pre-policy candidates.

## Amendments

Policy changes receive a new version and effective time. An amendment never
rewrites the selection provenance or frozen protocol of an earlier study.
