# Blind citation-calibration expectations

These expectations were written and frozen before any Qwen citation-review
output existed. They give the human/Codex outer loop a small, deliberately
varied benchmark for the six preregistered calibration sources. They are not
ground-truth labels and do not replace source-based adjudication.

The machine-readable ranges are in
`protocols/2607.17674/citation_calibration_expectations.v1.0.0.json`. They bind
the exact review plan and acquisition manifest. All six bibliographic
identities were expected to be matches.

The set includes straightforward direct uses (LoRA, Qwen2.5 model sizes, and
the core VAE description), claims where the target authors contribute part of
the comparison (the distinction from standard VAEs), co-cited claims where one
source carries only part of the sentence (Allman et al.), a modest extrapolation
from representation diversity to high-level strategies (Tuyls et al.), and one
intentionally difficult indirect use: calling self-consistency an application
of “exploration.” A reviewer that gives every occurrence a 9 or 10 therefore
fails to demonstrate useful calibration even if its JSON is valid.

When Qwen completes calibration, the operator compares its support class and
1–10 score with these ranges, reads every cited excerpt and rationale, and
records disagreements rather than coercing the output into the expected range.
A mismatch can reveal an expectation error, a Qwen error, or genuine ambiguity;
it is a trigger for documented adjudication, not an automatic scientific veto.
