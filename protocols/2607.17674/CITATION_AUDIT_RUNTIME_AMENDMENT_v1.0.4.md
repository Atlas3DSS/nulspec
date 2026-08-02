# Citation-audit runtime amendment v1.0.4

This prospective amendment follows an eligible v1.0.3 calibration attempt that
produced no accepted evidence record, teacher input, result, or release artifact.
The page-labeled presentation corrected the earlier page-locator behavior and
several candidates grounded exactly. Both permitted responses nevertheless
joined words across retained physical PDF line-wrap hyphens, so the unchanged
grounding validator rejected two candidates in each attempt on the first source.
The complete trace remains immutable with zero evidentiary weight.

Runtime v1.0.4 makes one further prospective presentation change for evidence
calls:

1. The immutable packet remains the validation input and retains the same hash,
   byte coverage, source identity, occurrences, page spans, and raw chunk text.
   The model-facing copy represents every extracted page as ordered
   `source_lines` produced by Python `splitlines(keepends=True)`. The compact
   ordered string array uses position as its one-based physical line number;
   the page retains its exact SHA-256 and line count. The runner fail-closes
   unless concatenating every line reconstructs its exact page and the pages
   cover every non-form-feed chunk character exactly once.
2. A hash-bound supplemental instruction requires each returned excerpt to be
   copied from exactly one physical source line. It tells the reviewer to prefer
   a shorter interior phrase before a split-word hyphen and to return no evidence
   for that chunk rather than reconstruct a sentence across lines.

The original immutable packets, GGUF, llama.cpp commit, context, full GPU
offload, thinking mode, seed, temperature, top-p, top-k, output ceilings,
response schemas, transport grammar, source order, calibration sources, retry
count, and client-side grounding validator remain unchanged. The transformed
presentation is serialized in every request trace; validation continues against
the original immutable packet.

The amended settings are immutable in
`citation_audit_config.v1.0.4.json`. A fresh trace directory, explicit config,
focused tests, all-packet reconstruction check, context-size audit, and fresh
lock-held runtime preflight are required before one new calibration. This
amendment does not authorize remaining-source review unless all six calibration
sources pass the unchanged gate.
