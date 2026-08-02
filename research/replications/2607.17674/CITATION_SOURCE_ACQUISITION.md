# Citation-source acquisition

**Protocol:** `2607.17674-citation-audit-v1.0.0`

**Input inventory:** 41 cited works and 74 citation occurrences, SHA-256
`471117efcde4eb55e8a6742dc00ffc0c291f30c821e071f56834c433cdabe43a`

**Final acquisition outcome:** complete on 2026-08-02 at 04:02:59 UTC. All 41
cited works have a PDF and nonempty extracted text; all 41 PDF hashes and all 41
text hashes are unique.

The complete ignored manifest is 67,395 bytes with SHA-256
`66fe09d96f2df62138a6f0e9820bc7e94c9fb8fc934d8d8bcb766277c29113d2`.
It binds every requested/final URL, retrieval attempt, byte count, PDF hash,
text-extraction hash, override rationale, and redistribution state. The source
set contains 143,161,240 PDF bytes and 4,230,676 extracted-text bytes.

## Immutable attempt history

| Attempt revision | Ready | Not acquired | Manifest SHA-256 |
|---|---:|---:|---|
| `4d50df8` | 32 | 9 | `24a43e75972871a035f0c7dbc78550341e98eae45f0753b5001775051f8e162e` |
| `15c2e3c` | 39 | 2 | `c7603fe0f17fce3b7734941560dfeb416ee042f72819980dd8f799dfa4ddc967` |
| `3484f3d` | 39 | 2 | `4430137e79b96fe543e233c46bbf8e6982c2a468d559dc800f7cd23b4edaf7cc` |
| `2af7662` | 41 | 0 | `66fe09d96f2df62138a6f0e9820bc7e94c9fb8fc934d8d8bcb766277c29113d2` |

No attempt was overwritten and the complete set was acquired afresh rather than
assembled opportunistically from earlier partial attempts.

## Route substitutions

Eleven sources use the tracked, identity-checked routes in
`protocols/2607.17674/citation_source_overrides.v1.json`:

- two official NeurIPS proceedings PDFs replace legacy short links that now
  return 404;
- one matching author arXiv preprint replaces a publisher page with no
  retrievable PDF; and
- eight archive captures preserve exact OpenReview or Project Euclid PDFs when
  live automated routes return verification pages, HTTP 403, or an HTTP
  downgrade.

The original cited URL remains in every record. Route substitution does not
substitute a different scholarly work. One archive retrieval for the immutable
1968 Yakowitz article postdates the target paper submission; that timing is
explicit in the manifest and override note.

## Boundary and next gate

PDFs and extracted text remain in ignored local storage. Their licenses have
not been individually cleared for redistribution, so none are committed or
published. The acquisition result is source preparation, not a citation
verdict.

The next gate is the six-key Qwen calibration pass registered in the citation
protocol. It has not begun. Raw Qwen prompts, streams, parsed records, timing,
usage, and errors will enter a new append-only review directory; teacher review
cannot begin until those calibration records are schema-valid.
