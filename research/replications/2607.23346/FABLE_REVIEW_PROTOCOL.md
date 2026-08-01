# One-shot final peer-review protocol

Frozen: 2026-08-01, before the Fable review request and before any Fable
response was observed.

## Role

Fable is the final independent release gate for this study. Its task is to
judge the completed public evidence bundle, not to collaborate on the analysis,
rewrite the scientific verdict, select a more favorable result, or conduct new
experiments. The frozen replication assessment remains **Not replicated** for
the public final-result recipe and **Inconclusive** for the underlying method.

Fable receives a deterministic packet containing the principal reports,
protocols, error ledger, author-email draft, source hashes, and compact machine
evidence. The packet is committed before invocation. The public review result
binds both the packet SHA-256 and reviewed Git commit. Full prompt, response,
stderr, and attempt state are retained in the ignored lab archive; their hashes
and the complete structured verdict are public.

## Exactly one invocation

There is exactly one Fable invocation for this release candidate. The runner
writes a durable attempt marker before starting and refuses to overwrite or
repeat it. There is no resubmission after a substantive `FAIL`. A safeguard
refusal, malformed response, interrupted invocation, or other technical failure
fails closed as `HARD_FAIL` and requires human review; it is not silently
retried.

This is one adjudication, not an iterative review conversation. An ordinary
`FAIL` goes through the three-action closure path without human escalation;
only `HARD_FAIL` requires a human decision on the publication gate.

## Decisions

Fable must return one of three decisions:

1. `PASS`: no required correction remains. Publication is authorized and the
   author-email draft becomes eligible for mandatory final human approval.
2. `FAIL`: the bundle is publishable after exactly three concrete action items.
   Research implements and documents all three, runs deterministic validation,
   and then publishes without asking Fable again. Closing all three actions is
   treated as satisfying Fable's conditional approval; the author-email draft
   becomes eligible for mandatory final human approval only after that closure.
3. `HARD_FAIL`: the problem cannot responsibly be reduced to three corrections,
   or human judgment is required. Publication and author email stop until a
   human records a decision.

Suggestions are not allowed outside this contract: `PASS` has zero action
items, `FAIL` has exactly three, and `HARD_FAIL` has zero action items plus a
specific reason for human review.

## Review criteria

Fable must independently assess:

- scientific fidelity to the targeted paper claim;
- consistency between prose and machine evidence;
- statistical and uncertainty language;
- separation of replication, reconstruction, extensions, and post-hoc work;
- reproducibility and provenance;
- origin-separated error transparency;
- correctness of the publication handoff; and
- fairness and factual accuracy of the author email.

A disclosed limitation is not automatically a failure. A failure should
identify a correction that materially improves truthfulness, reproducibility,
or fairness. Fable cannot change a frozen numerical result, suppress a null
result, or reinterpret missing evidence as confirmation.

## Closure and email gate

For `FAIL`, the closure record must preserve Fable's three action identifiers,
describe each implemented change, link its evidence, and state that no second
Fable invocation occurred. The local release gate permits publication only for
`PASS`, a fully closed three-action `FAIL`, or a recorded human disposition
after `HARD_FAIL`.

The author email is downstream of this peer-review gate but has an additional
mandatory human gate. Fable can make the exact draft eligible for approval; it
can never authorize dispatch. A separate human approval record must bind the
email draft, final review, and any action closure before the dispatch control
opens. Fable is told this in the review prompt.
