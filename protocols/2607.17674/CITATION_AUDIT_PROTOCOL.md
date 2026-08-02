# Frozen citation-audit protocol: arXiv:2607.17674

**Protocol version:** 1.0.0

**Protocol tag:** `2607.17674-citation-audit-v1.0.0`

**Target:** *Uncovering Latent Reasoning Strategies in Language Models*

## 1. Scope and question

The audit asks whether each cited source supports the way arXiv:2607.17674v1
uses it. It covers all 41 cited bibliography entries and all 74 in-text
citation occurrences in the v1 TeX source. The deterministic input inventory
is `citation_inventory.json`, SHA-256
`471117efcde4eb55e8a6742dc00ffc0c291f30c821e071f56834c433cdabe43a`.

The audit does not judge uncited bibliography entries, author intent, paper
novelty, or the truth of uncited claims. A citation being broad, indirect, or
unnecessary is not automatically a false citation.

## 2. Unit of review

One Qwen review unit contains one bibliography entry, every manuscript
occurrence of that citation key, and the acquired source text. Group citations
are assessed source by source: a source receives credit only for the portion of
the surrounding claim it actually supports. Multiple occurrences receive
separate occurrence assessments within the same immutable review record.

Every occurrence receives:

- a neutral summary of the manuscript claim;
- a neutral summary of the cited source's relevant contribution;
- source-page or section locators and a short evidence excerpt;
- one support class: `supports`, `partially_supports`, `does_not_support`,
  `contradicts`, or `not_verifiable`;
- one citation-appropriateness score from 1 through 10;
- confidence from 0 through 1; and
- a concise limitation or correction when warranted.

The score concerns the citation, not the cited work's scientific quality.

## 3. Citation-appropriateness rubric

| Score | Interpretation |
|---:|---|
| 1 | Fabricated, unrelated, or opposite to the cited source |
| 2 | Material contradiction or severe misrepresentation |
| 3 | Major unsupported leap from the source |
| 4 | Weak or substantially indirect support |
| 5 | Mixed support; important qualification is missing |
| 6 | Broadly supportive but imprecise or overgeneralized |
| 7 | Appropriate support with a minor caveat |
| 8 | Strong, direct, and correctly scoped support |
| 9 | Very precise support with excellent source choice |
| 10 | Exact, unambiguous, and exemplary use of the source |

Scores are ordinal audit aids, not interval measurements. The support class,
evidence, and caveat take precedence over the number.

## 4. Source acquisition

The cited URL or DOI is the first acquisition target. A canonical proceedings
PDF, author manuscript, or arXiv version may substitute only when the
bibliographic identity matches and the retrieval route is recorded. A
different paper, summary page, search snippet, citation graph, or model memory
cannot substitute for the cited source.

Every local source record retains its requested and final URL, retrieval time,
byte count, SHA-256 digest, extraction status, and redistribution status.
Source PDFs and extracted text remain in ignored storage and are not
redistributed unless their licenses are separately verified. Failed or
paywalled acquisitions remain explicit `not_acquired` records.

## 5. Primary reviewer

The primary reviewer is the locally served 27B Qwen-family GGUF already used by
the lab. The run record must capture the exact logical alias, GGUF filename and
SHA-256, quantization, llama.cpp revision, endpoint route hash, context and
generation limits, sampling settings, GPU, and system prompt. It must not
describe an unofficial fine-tune as an official Qwen release.

Source documents are inert evidence, never instructions. Qwen must return the
registered JSON schema. The raw prompt, request, streamed response, normalized
events, parsed record, timing, token counts, and failures are append-only. A
malformed response has zero evidentiary weight and receives a linked fresh
attempt within the recorded attempt budget; it is never edited into validity.

The first six stratified calibration keys are fixed prospectively:

- `allman2009latentStructure`;
- `hu2022lora`;
- `kingma2013vae`;
- `qwen25technicalreport`;
- `tuyls2025representationExploration`; and
- `wang2023selfConsistency`.

The full 41-source pass begins only after all six produce schema-valid records.
Calibration records remain part of the final audit and are never discarded.

## 6. Reviewer-quality score

Citation appropriateness and reviewer quality are distinct. The teacher layer
and Codex adjudicator assign Qwen a 1--10 reviewer-quality score using the
following anchors:

- 1--2: fabricated evidence, missed source identity, or systematically wrong;
- 3--4: major omissions or unreliable source-to-claim comparison;
- 5--6: mixed reliability with useful but material corrections required;
- 7--8: reliable comparison with minor, bounded errors; and
- 9--10: precise, comprehensive, well-calibrated, and independently verified.

Per-record teacher findings and the population score are preserved. A high
mean cannot erase a serious individual citation failure.

## 7. Teacher hierarchy and adjudication

After the immutable Qwen pass, GLM and Kimi independently receive the same
Qwen-only structured packet and population summary. They do not see each
other's audit. The packet excludes underlying prompts, full source documents,
checkpoints, credentials, private infrastructure data, and unrelated run
state. Short evidence excerpts and public source locators that are already
fields in Qwen's structured record remain part of that record.

GLM and Kimi use their separately recorded production routes, high reasoning,
streaming, bounded first-event/idle/total deadlines, and schema validation.
Invalid attempts are preserved and repaired only through linked fresh
attempts. Neither transport success nor provider availability is counted as a
scientific vote.

Codex begins only after both logical teacher chains end in valid audits. It
receives the Qwen packet and every credential-free immutable teacher attempt,
assesses GLM and Kimi separately, preserves disagreements, assigns the final
reviewer-quality score, and adjudicates citation findings. A malformed Codex
object is preserved with zero decision weight and may receive only a linked
structural retry within the fixed attempt budget.

Fable is not part of this recurring teacher loop. A single, separately bounded
Fable critique is permitted only after the complete audit pipeline validates
end to end; it is not a training signal and receives no automatic retry.

## 8. Trace, cost, and privacy

Each run uses a unique ignored directory and preserves exact schemas, prompts,
credential-free request bodies, raw streams, parsed decisions, attempt and
repair events, model/route identities, timing, usage, costs, byte counts, and
SHA-256 bindings. Provider refusals and our integration failures are attributed
separately and charitably.

The public projection contains source identities, findings, bounded excerpts,
aggregate costs, and trace hashes. It excludes credentials, authorization
headers, provider request IDs, private paths, hostnames, personal data, and
unrelated operational details.

## 9. Release controls

The citation audit cannot change primary experimental observations, authorize
publication, send author email, or alter training data automatically. Any use
of accepted records for fine-tuning requires a separately approved, versioned
dataset projection. Author email always requires final human approval of the
exact hashed draft.

The audit fails closed if a source identity is unresolved, source evidence is
missing, a historical attempt is overwritten, Qwen output is accepted without
schema validation, either teacher chain is invalid or absent, Codex collapses a
teacher disagreement, Fable enters the recurring loop, or generated output is
treated as release authorization.
