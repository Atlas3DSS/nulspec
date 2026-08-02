# Citation-audit runtime amendment v1.0.3

This prospective amendment follows an eligible v1.0.2 calibration attempt that
produced no accepted evidence record, teacher input, result, or release artifact.
Both allowed generations completed structurally, but the exact grounding
validator rejected every candidate used by the second attempt on the first
source. The trace is retained in full with zero evidentiary weight.

The failure audit found two model-facing usability problems rather than a
validator defect. The model silently dehyphenated words split by extracted-PDF
line wrapping, even though the contract permits whitespace normalization only.
It also inferred extracted-page numbers from document position and printed page
headers instead of locating each excerpt inside the supplied character spans.
The validator correctly rejected those altered excerpts and wrong locators.

Runtime v1.0.3 makes one prospective presentation change for evidence calls:

1. The immutable packet remains the validation input and retains the same hash,
   byte coverage, source identity, occurrences, and raw chunk text. The
   model-facing copy replaces the raw `source_chunk.text` field with ordered
   `source_chunk.extracted_pages` entries derived exactly from the frozen page
   spans. Each entry contains one authoritative page number, the exact page
   substring, and its SHA-256. The runner fail-closes unless these entries cover
   every non-form-feed character exactly once and omit only form-feed page
   delimiters.
2. A hash-bound supplemental instruction tells the reviewer to copy an excerpt
   directly from one labeled page, preserve line-wrap hyphens, and prefer a
   shorter exact substring rather than repairing PDF text. The original v1.0.1
   evidence prompt remains unchanged and bound by the immutable review plan.

The GGUF, llama.cpp commit, context, full GPU offload, thinking mode, seed,
temperature, top-p, top-k, output ceilings, schemas, transport grammar,
calibration sources, source order, retry count, and every client-side acceptance
rule remain unchanged. The transformed presentation is serialized in every
request trace; validation still runs only against the original immutable packet.

The amended settings are immutable in
`citation_audit_config.v1.0.3.json`. A fresh trace directory, explicit config,
focused tests, and a fresh lock-held runtime preflight are required before a new
calibration. This amendment does not authorize remaining-source review unless
all six calibration sources pass the unchanged gate.
