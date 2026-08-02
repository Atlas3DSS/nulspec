# Citation-audit runtime amendment v1.0.2

This prospective amendment follows one terminal calibration attempt with zero
evidentiary weight. That attempt is preserved in full and documented in
`CITATION_REVIEW_EXECUTION.md`; it produced no accepted citation record,
teacher input, result, or release artifact.

The pinned llama.cpp runtime rejected the v1.0.1 evidence schema as a decoding
grammar because nested `maxItems` and `maxLength` bounds expanded past its sane
grammar limit. It nevertheless processed the request without that grammar.
Both allowed attempts then spent their 2,048 output tokens in thinking and
returned no final content. The client correctly rejected both.

Runtime v1.0.2 makes two prospective changes:

1. The decoding grammar retains the canonical schema's object fields, required
   keys, types, nesting, and enumerations but omits quantitative length, item,
   and numeric bounds. The complete unmodified schema remains the sole
   acceptance contract and is saved separately in every attempt. Client-side
   identity, coverage, range, excerpt-grounding, and completeness validation is
   unchanged and remains fail closed.
2. Thinking remains enabled. The evidence output ceiling increases from 2,048
   to 8,192 tokens and synthesis from 4,096 to 12,288 tokens. Temperature,
   seed, top-p, top-k, context, model, packet contents, prompts, source order,
   calibration set, retry count, and all substantive validation rules remain
   unchanged. A response that reaches either new ceiling without final content
   still has zero weight.

The amended settings are immutable in
`citation_audit_config.v1.0.2.json`. A fresh trace directory and explicit
`--config` argument are required. Before a scientific retry, the exact pinned
server must accept both transported schemas without a grammar-parser warning,
and the focused runner tests must pass. This amendment is frozen by tag
`2607.17674-citation-audit-runtime-v1.0.2`; the source/evidence packet contract
remains v1.0.1 and its hashes are unchanged.
