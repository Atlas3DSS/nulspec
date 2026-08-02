# Citation-review packetization record

The v1.0.1 citation-audit amendment was prepared before any Qwen citation
prompt was issued. It binds 41 cited sources and all 74 manuscript occurrences
to 112 contiguous evidence packets. The packets cover 4,230,676 extracted-text
bytes exactly once, with zero overlap and zero gaps; no packet exceeds 48,000
UTF-8 bytes.

The validated ignored packet root is:

`research/replications/2607.17674/work/citation-review/packet-attempt-20260802T042752Z-v1.0.1`

- `review-plan.json` SHA-256:
  `66d1987c750db0d6a066e5efd5972caf54a294569ef8b8bd524f508530eef327`
- `packet-validation.json` SHA-256:
  `07523ce84afd797f49437d275df76b93cc1b1994c7d00f93a2b3168dbeb57973`

The source texts and packets remain ignored because cited-paper redistribution
rights were not individually verified. The tracked builder, validator,
schemas, prompts, and configuration are sufficient to reconstruct and check
the packet tree from the acquired source manifest.

## Attempt history

- `packet-attempt-20260802T041339Z-v1.0.1` stopped on its independent size
  assertion because the first chunker admitted a newline one byte beyond its
  ceiling. The partial directory is preserved; see `LRS-LOCAL-017`.
- `packet-attempt-20260802T041519Z-v1.0.1` completed under an interim,
  pre-freeze generation budget. It is preserved but ineligible because the
  output budgets and thinking flag were then tightened prospectively.
- `packet-attempt-20260802T042752Z-v1.0.1` was rebuilt cleanly against the final
  amendment inputs and passed independent coverage and hash validation.

No packet from any attempt had been sent to Qwen when this record was written.
The fixed six-source calibration gate must pass before the remaining 35 source
reviews begin.

## Reconstruction

```bash
python scripts/prepare_2607_17674_citation_review.py \
  --acquisition-manifest <ignored-acquisition-root>/acquisition-manifest.json \
  --source-root <ignored-acquisition-root> \
  --output-root <new-ignored-packet-root>

python scripts/validate_2607_17674_citation_packets.py \
  --review-plan <new-ignored-packet-root>/review-plan.json \
  --packet-root <new-ignored-packet-root> \
  --output <new-ignored-packet-root>/packet-validation.json
```
