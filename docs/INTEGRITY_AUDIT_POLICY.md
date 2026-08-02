# Citation and textual-integrity audit policy

## Purpose

NULSPEC may use otherwise idle, safely isolated compute to check whether a
paper's citations support the claims attached to them and to screen for
potentially meaningful textual overlap with earlier public work. These audits
can run while a larger experiment is waiting on a resource, but they do not
replace reproduction of the paper's scientific results.

The two audit types remain distinct:

- **Citation audit:** identify each citation occurrence, recover the cited
  source, locate relevant source evidence, and assess whether the target
  paper's local claim is supported, qualified, contradicted, merely
  background, or not reviewable.
- **Textual-overlap screen:** identify exact or near-exact passage overlap and
  semantic candidates for closer review, then evaluate attribution and
  chronology. The automated stage does not decide whether plagiarism occurred.

## Evidence pipeline

1. Bind the target paper version, bibliography, source URLs, acquisition time,
   content hashes, extraction tooling, and redistribution status.
2. Resolve source identity before comparing content. Record substitutions such
   as an author preprint for a blocked publisher copy without pretending that
   the retrieval route was the cited route.
3. Normalize text conservatively while retaining page, section, line, and raw
   text anchors. Keep equations, tables, references, and boilerplate separable
   so they can be included or excluded explicitly.
4. Run deterministic exact-match and near-match retrieval first. Suitable
   methods include token shingles, winnowing, MinHash/LSH, and local lexical
   search. Record parameters, software revisions, candidate counts, and every
   filtering decision.
5. Use embeddings or a local language model only to rank and explain retained
   candidates. Preserve the full prompts, streams, responses, parse failures,
   timing, resource use, and cost. Model output cannot erase or manufacture a
   deterministic match.
6. For each retained passage, record the earlier text, target text, dates,
   overlap span, nearby citation and quotation context, shared authorship,
   likely benign explanations, and the evidence needed to resolve ambiguity.
7. Validate the complete trace and send model judgments through the registered
   reviewer hierarchy. Sensitive unresolved findings require human review.

## Interpretation safeguards

- Call automated outputs **overlap candidates**, **citation findings**, or
  **integrity-review leads**. Do not label an author or paper plagiaristic from
  a similarity score.
- Exclude or separately label references, license text, prompts, dataset
  descriptions, standard definitions, conventional methods language, and
  phrases too short or common to be probative.
- Check preprint and publication chronology. A later-dated source cannot be
  evidence that the target copied an earlier work, and multiple versions of
  the same work are not independent sources.
- Treat legitimate quotation, clear citation, self-reuse, shared-author
  manuscripts, and mandated template language as distinct cases rather than
  one undifferentiated score.
- Preserve negative results: finding no meaningful overlap within the defined
  corpus is reportable only as a bounded screen, never proof that no overlap
  exists elsewhere.
- Public reports include the search corpus and its coverage limits. Restricted
  full texts stay out of Git and public bundles; hashes and short,
  context-necessary evidence excerpts bind the finding.

## Evidence-integrity heatmap

Public summaries may use a claim-level heatmap to make a large audit legible,
but it measures observable evidence conditions rather than author character or
intent. Rows bind individual claims or citation occurrences; columns use a
small typed taxonomy:

- source identity and version match;
- citation support and qualification;
- claim strength relative to the cited evidence;
- contradictory source evidence;
- citation completeness and primary-source proximity;
- textual provenance and attribution;
- statistical or reporting consistency; and
- code, data, and artifact consistency.

Every nonempty cell links to its evidence record. **Severity** (likely effect
on interpretation) and **confidence** (strength and coverage of the evidence)
are separate ordinal fields; neither is a probability of misconduct. The
display must distinguish `not_checked`, `no_issue_observed`, `uncertain`, and
`finding` so missing coverage cannot look like a clean result. Color is never
the only carrier of meaning.

The heatmap has no person score, author ranking, aggregate "fraud" score, or
automatic misconduct label. Terms such as fraud, fabrication, plagiarism, and
research misconduct require competent human or institutional findings and are
not inferred by this pipeline. Public prose instead names the reproducible
observation—for example, "the cited experiment does not test this claim" or
"this passage overlaps an earlier source without a nearby attribution"—then
states plausible benign explanations and the consequence for the paper's
claim. Charitable wording may not hide a material discrepancy.

Published audits retain version history and a visible author-response or
correction path. A later clarification never overwrites the originally audited
version; it becomes linked follow-up evidence.

## Prepublication outreach and elevated allegation gate

A reproducible non-replication result is scientifically distinct from an
allegation of plagiarism, fabrication, falsification, or fraud. The former may
be published with calibrated limitations while a potential misconduct finding
remains privately embargoed.

Before NULSPEC publicly uses plagiarism or misconduct language, it must:

1. freeze and hash the private evidence packet;
2. have at least two qualified humans independently review the underlying
   source material, chronology, attribution context, and benign alternatives;
3. prepare a neutral, evidence-specific inquiry for the target paper's
   corresponding team and, for textual-overlap concerns, the earlier source
   team when contactable;
4. obtain final human approval for the exact outbound message before sending;
5. provide a declared, reasonable response window; and
6. incorporate the response fairly, or state the contact attempts and lack of
   response without treating silence as admission.

Model agreement, similarity magnitude, failed replication, anomalous
statistics, or missing artifacts cannot satisfy this gate by themselves.
Plagiarism language additionally requires substantial and distinctive earlier
text, verified source identity and chronology, absent or materially inadequate
attribution, and documented exclusion of common language, legitimate
quotation, related versions, templates, and shared-author explanations. Fraud
language requires direct evidence of intentional deception or a competent
authoritative finding; inconsistent results alone do not establish intent.

A truly egregious exception may shorten the response wait, but it does not
permit automatic publication. At least two human reviewers must unanimously
document the direct evidence, the public-interest reason that delay would be
harmful, all attempted outreach, and approval of the exact public wording.
Named allegations should receive appropriate independent subject-matter and
legal review before release. This exception never grants a model or automated
pipeline publication authority.

## Scheduling and corpus reuse

Integrity jobs run at low priority inside explicit CPU, RAM, and GPU limits.
They must stop or defer before pressuring a primary run or an unrelated
workload. Source fetching, PDF extraction, hashing, lexical indexing, and
MinHash screening normally use CPU and can occupy periods when accelerator
headroom is too small for training. Model review uses only explicitly assigned
residual GPU capacity.

Schema-valid traces and subsequent teacher/human scores may enter a
versioned training corpus for improving the local reviewer. Raw copyrighted
papers, credentials, private data, and unredacted provider metadata do not.
Training reuse must retain the originating prompt/schema/model identities,
review score, adjudication history, and license or redistribution decision.
