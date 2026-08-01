#!/usr/bin/env python3
"""Build and validate sanitized external-review ledgers for this study.

The exact provider traces remain in the ignored lab archive. This exporter
retains their hashes, byte counts, costs, useful model text, and human labels
while removing request/session identifiers and private machine context.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


PACKET_SHA256 = "5eabac56ae0d25cecc11a308e669d4de95911e4e3f7c81f533b66eafe9ac53ea"
PROMPT_SHA256 = "182d3718f8c38aef22585ad44c5fd2d44d56e54b21c3772b302322ec9ee9b95d"
REVIEWED_COMMIT = "68188afc7305e5168d33c5278968f7a26b403a40"
CATALOG_SHA256 = "86b3b7a89e1340fcb35730d74e0c550e4896915943db341e5ca632264754b630"
CATALOG_REVERIFIED_AT = "2026-08-01T18:07:18.601788Z"
FABLE_REFUSAL_ID = "FABLE-REFUSAL-20260801-001"
CONSENSUS_DECIDED_AT = "2026-08-01T18:16:18Z"

MODELS = {
    "z-ai/glm-5.2-20260616": {
        "family": "GLM",
        "requested_id": "z-ai/glm-5.2",
        "canonical_slug": "z-ai/glm-5.2-20260616",
        "catalog_entry_sha256": (
            "3cc2711d55995750ac3cf8d6b94929992db3197342221012eb4df9de5308e0a4"
        ),
        "context_length": 1_048_576,
        "catalog_created_unix": 1_781_631_930,
        "catalog_pricing_usd_per_token": {
            "prompt": "0.0000007168",
            "completion": "0.0000022528",
            "input_cache_read": "0.00000013312",
        },
    },
    "moonshotai/kimi-k3-20260715": {
        "family": "Kimi",
        "requested_id": "moonshotai/kimi-k3",
        "canonical_slug": "moonshotai/kimi-k3-20260715",
        "catalog_entry_sha256": (
            "76e5f2549c3c848056871c2cb9db88b758cf606ee29acfa464f376a00c22704e"
        ),
        "context_length": 1_048_576,
        "catalog_created_unix": 1_784_215_858,
        "catalog_pricing_usd_per_token": {
            "prompt": "0.000003",
            "completion": "0.000015",
            "input_cache_read": "0.0000003",
        },
    },
}

FORBIDDEN_PUBLIC_PATTERNS = {
    "request identifier": re.compile(r"\breq_[A-Za-z0-9]+\b"),
    "request field": re.compile(r'"request_id"\s*:'),
    "session field": re.compile(r'"session_id"\s*:'),
    "UUID field": re.compile(r'"uuid"\s*:'),
    "private Unix path": re.compile(r"/(?:home|Users)/[^\s\"']+"),
    "private Windows path": re.compile(r"[A-Za-z]:\\\\Users\\\\"),
    "credential": re.compile(
        r"(?:sk-or-v1-|OPENROUTER_API_KEY\s*[=:]\s*[^\s]+)", re.IGNORECASE
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "check"))
    parser.add_argument("--study-root", type=Path, default=Path.cwd())
    parser.add_argument("--catalog", type=Path)
    return parser.parse_args()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def pretty(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    return {"bytes": len(payload), "sha256": sha256_bytes(payload)}


def load(path: Path) -> dict[str, Any] | list[Any]:
    return json.loads(path.read_text())


def assert_public_safe(label: str, text: str) -> None:
    for reason, pattern in FORBIDDEN_PUBLIC_PATTERNS.items():
        if pattern.search(text):
            raise ValueError(f"{label}: contains {reason}")


def fable_event(study: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    work = study / "work/fable_final_review"
    raw = load(work / "raw.json")
    assert isinstance(raw, list)
    result = next(row for row in raw if row.get("type") == "result")
    refusal = next(
        row for row in raw if row.get("subtype") == "model_refusal_no_fallback"
    )
    provider_message = str(result["result"])
    provider_message = re.sub(
        r"\n\nRequest ID:.*$", "", provider_message, flags=re.DOTALL
    )
    assert_public_safe("sanitized Fable provider message", provider_message)
    attempt = load(work / "attempt.json")
    assert isinstance(attempt, dict)
    public = load(study / "results/fable_final_peer_review.json")
    assert isinstance(public, dict)
    packet = file_record(study / "results/fable_final_review_packet.json")
    if packet["sha256"] != PACKET_SHA256:
        raise ValueError("Fable packet hash changed")
    artifacts = {
        "attempt": file_record(work / "attempt.json"),
        "prompt": file_record(work / "prompt.txt"),
        "raw_response": file_record(work / "raw.json"),
        "stderr": file_record(work / "stderr.txt"),
    }
    if artifacts["prompt"]["sha256"] != PROMPT_SHA256:
        raise ValueError("Fable prompt hash changed")
    if (
        artifacts["raw_response"]["sha256"]
        != public["invocation"]["raw_response_sha256"]
    ):
        raise ValueError("Fable raw-response hash differs from public result")
    usage = result["usage"]
    model_usage = result["modelUsage"]
    event = {
        "event_id": FABLE_REFUSAL_ID,
        "event_type": "reviewer_safeguard_refusal",
        "provider": "Anthropic",
        "reviewer": "Fable",
        "model": "claude-fable-5",
        "started_at_utc": attempt["started_at_utc"],
        "completed_at_utc": attempt["completed_at_utc"],
        "elapsed_seconds": public["invocation"]["elapsed_seconds"],
        "http_status": None,
        "model_invoked": True,
        "consensus_eligible": False,
        "validation_status": "technical_hard_fail",
        "declared_verdict": None,
        "findings_returned": 0,
        "failure": {
            "category": refusal["api_refusal_category"],
            "stop_reason": result["stop_reason"],
            "terminal_reason": result["terminal_reason"],
            "provider_message_sanitized": provider_message,
        },
        "binding": {
            "reviewed_commit": REVIEWED_COMMIT,
            "packet_sha256": PACKET_SHA256,
            "packet_bytes": packet["bytes"],
            "prompt_sha256": PROMPT_SHA256,
            "prompt_bytes": artifacts["prompt"]["bytes"],
        },
        "usage": usage,
        "model_usage": model_usage,
        "charged_cost_usd": result["total_cost_usd"],
        "trace": {
            "retention": "ignored_immutable_lab_archive",
            "public": False,
            "artifacts": artifacts,
        },
        "publication_consequence": (
            "Fable HARD_FAIL; no resubmission; invoke the one-pair GLM/Kimi "
            "supplemental disposition and otherwise fail closed for human review."
        ),
    }
    trace = {
        "schema_version": "nulspec-sanitized-review-training-trace-v1",
        "event_id": FABLE_REFUSAL_ID,
        "provider": "Anthropic",
        "model": "claude-fable-5",
        "input_binding": event["binding"],
        "response": {
            "provider_message_sanitized": provider_message,
            "refusal_category": refusal["api_refusal_category"],
            "stop_reason": result["stop_reason"],
            "terminal_reason": result["terminal_reason"],
        },
        "usage": usage,
        "model_usage": model_usage,
        "charged_cost_usd": result["total_cost_usd"],
        "human_label": {
            "class": "technical_safeguard_refusal_before_substantive_review",
            "scientific_evidence": False,
            "findings_returned": 0,
            "consensus_eligible": False,
        },
        "raw_trace": event["trace"],
    }
    return event, trace


def openrouter_event(
    study: Path,
    *,
    event_id: str,
    source: str,
    canonical_slug: str,
    consensus_eligible: bool,
    human_class: str,
    model_invoked: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_dir = study / source
    summary = load(source_dir.parent / "summary.json")
    assert isinstance(summary, dict)
    row = next(
        item
        for item in summary["results"]
        if item["model"]["canonical_slug"] == canonical_slug
    )
    attempt_path = source_dir / "attempt.json"
    raw_path = source_dir / "raw.json"
    attempt_record = file_record(attempt_path)
    raw_record = file_record(raw_path)
    if raw_record["sha256"] != row["raw_response_sha256"]:
        raise ValueError(f"{event_id}: raw hash mismatch")
    model = MODELS[canonical_slug]
    if row["model"]["catalog_entry_sha256"] != model["catalog_entry_sha256"]:
        raise ValueError(f"{event_id}: catalog entry hash mismatch")
    raw = load(raw_path)
    assert isinstance(raw, dict)
    content: str | None = None
    parsed: dict[str, Any] | None = None
    finish_reason: str | None = None
    native_finish_reason: str | None = None
    provider_model: str | None = None
    error: dict[str, Any] | None = None
    choices = raw.get("choices")
    if isinstance(choices, list) and choices:
        choice = choices[0]
        content = choice.get("message", {}).get("content")
        finish_reason = choice.get("finish_reason")
        native_finish_reason = choice.get("native_finish_reason")
        provider_model = raw.get("model")
        if isinstance(content, str):
            try:
                candidate = json.loads(content)
            except json.JSONDecodeError:
                candidate = None
            if isinstance(candidate, dict):
                parsed = candidate
    elif isinstance(raw.get("error"), dict):
        error = {
            "message": str(raw["error"].get("message") or ""),
            "code": raw["error"].get("code"),
        }
    declared = parsed.get("verdict") if parsed else None
    if declared is None and isinstance(content, str):
        match = re.search(r'"verdict"\s*:\s*"(PASS|FAIL|HARD_FAIL)"', content)
        declared = match.group(1) if match else None
    if content is not None:
        assert_public_safe(f"{event_id} model content", content)
    if error is not None:
        assert_public_safe(f"{event_id} transport error", pretty(error))
    usage = row.get("usage") or {}
    cost = float(usage.get("cost") or 0.0)
    event = {
        "event_id": event_id,
        "event_type": (
            "supplemental_model_review" if model_invoked else "transport_failure"
        ),
        "provider": "OpenRouter",
        "reviewer_family": model["family"],
        "requested_model": model["requested_id"],
        "canonical_model": canonical_slug,
        "provider_reported_model": provider_model,
        "started_at_utc": row["started_at_utc"],
        "completed_at_utc": row["completed_at_utc"],
        "elapsed_seconds": row["elapsed_seconds"],
        "http_status": row["http_status"],
        "model_invoked": model_invoked,
        "consensus_eligible": consensus_eligible,
        "validation_status": row["status"],
        "declared_verdict": declared,
        "validated_verdict": (
            row["decision"]["verdict"]
            if isinstance(row.get("decision"), dict)
            else None
        ),
        "failure": row.get("failure"),
        "finish_reason": finish_reason,
        "native_finish_reason": native_finish_reason,
        "findings_returned": (
            len(parsed.get("checks", [])) if isinstance(parsed, dict) else 0
        ),
        "binding": {
            "reviewed_commit": REVIEWED_COMMIT,
            "packet_sha256": row["packet_sha256"],
            "prompt_sha256": row["prompt_sha256"],
            "catalog_entry_sha256": model["catalog_entry_sha256"],
        },
        "usage": usage,
        "charged_cost_usd": cost,
        "trace": {
            "retention": "ignored_immutable_lab_archive",
            "public": False,
            "artifacts": {
                "attempt": attempt_record,
                "raw_response": raw_record,
            },
        },
        "human_label": human_class,
    }
    trace = {
        "schema_version": "nulspec-sanitized-review-training-trace-v1",
        "event_id": event_id,
        "provider": "OpenRouter",
        "requested_model": model["requested_id"],
        "canonical_model": canonical_slug,
        "provider_reported_model": provider_model,
        "input_binding": event["binding"],
        "response": {
            "content": content,
            "parsed_content": parsed,
            "transport_error": error,
            "finish_reason": finish_reason,
            "native_finish_reason": native_finish_reason,
        },
        "usage": usage,
        "charged_cost_usd": cost,
        "human_label": {
            "class": human_class,
            "declared_verdict": declared,
            "validated_verdict": event["validated_verdict"],
            "consensus_eligible": consensus_eligible,
            "scientific_evidence": False,
        },
        "raw_trace": event["trace"],
    }
    return event, trace


def build_payloads(study: Path, catalog: Path | None) -> dict[Path, str]:
    repo = study.parents[2]
    fable, fable_trace = fable_event(study)
    specs = [
        (
            "OR-TRANSPORT-20260801-001",
            "work/openrouter_fallback_reviews/z-ai-glm-5-2",
            "z-ai/glm-5.2-20260616",
            False,
            "authentication_transport_failure_no_model_invocation",
            False,
        ),
        (
            "OR-TRANSPORT-20260801-002",
            "work/openrouter_fallback_reviews/moonshotai-kimi-k3",
            "moonshotai/kimi-k3-20260715",
            False,
            "authentication_transport_failure_no_model_invocation",
            False,
        ),
        (
            "OR-REVIEW-20260801-001",
            "work/openrouter_fallback_reviews_transport_recovery_01/z-ai-glm-5-2",
            "z-ai/glm-5.2-20260616",
            True,
            "primary_pair_schema_invalid_wrong_pass_next_step",
            True,
        ),
        (
            "OR-REVIEW-20260801-002",
            "work/openrouter_fallback_reviews_transport_recovery_01/moonshotai-kimi-k3",
            "moonshotai/kimi-k3-20260715",
            True,
            "primary_pair_truncated_invalid_json",
            True,
        ),
        (
            "OR-REVIEW-20260801-003",
            "work/openrouter_fallback_reviews_contract_recovery_01/z-ai-glm-5-2",
            "z-ai/glm-5.2-20260616",
            False,
            "ineligible_additional_call_after_primary_pair",
            True,
        ),
    ]
    events = [fable]
    traces = [fable_trace]
    for event_id, source, slug, eligible, label, invoked in specs:
        event, trace = openrouter_event(
            study,
            event_id=event_id,
            source=source,
            canonical_slug=slug,
            consensus_eligible=eligible,
            human_class=label,
            model_invoked=invoked,
        )
        events.append(event)
        traces.append(trace)

    openrouter_cost = round(
        sum(
            row["charged_cost_usd"] for row in events if row["provider"] == "OpenRouter"
        ),
        8,
    )
    fable_cost = round(fable["charged_cost_usd"], 8)
    total_cost = round(fable_cost + openrouter_cost, 8)
    ledger = {
        "schema_version": "nulspec-external-review-ledger-v1",
        "study_id": "260723346",
        "target_arxiv_id": "2607.23346v1",
        "generated_at_utc": CONSENSUS_DECIDED_AT,
        "append_only": True,
        "binding": {
            "reviewed_commit": REVIEWED_COMMIT,
            "packet_sha256": PACKET_SHA256,
            "prompt_sha256": PROMPT_SHA256,
        },
        "totals": {
            "provider_request_events": len(events),
            "model_invocations": sum(bool(row["model_invoked"]) for row in events),
            "consensus_eligible_model_invocations": sum(
                bool(row["consensus_eligible"]) for row in events
            ),
            "findings_returned_by_consensus_eligible_valid_reviews": 0,
            "anthropic_usd": fable_cost,
            "openrouter_usd": openrouter_cost,
            "total_usd": total_cost,
        },
        "interpretation": (
            "Review outcomes are release-process evidence only. They do not alter "
            "the frozen scientific result."
        ),
        "events": events,
    }
    primary = [
        row
        for row in events
        if row["event_id"] in {"OR-REVIEW-20260801-001", "OR-REVIEW-20260801-002"}
    ]
    if len(primary) != 2:
        raise ValueError("primary supplemental pair is incomplete")
    consensus = {
        "schema_version": "nulspec-supplemental-review-consensus-v1",
        "study_id": "260723346",
        "decided_at_utc": CONSENSUS_DECIDED_AT,
        "source_fable_refusal_id": FABLE_REFUSAL_ID,
        "source_fable_result_sha256": file_record(
            study / "results/fable_final_peer_review.json"
        )["sha256"],
        "binding": ledger["binding"],
        "policy": {
            "trigger": "Fable technical HARD_FAIL",
            "required_reviewers": ["GLM", "Kimi"],
            "same_immutable_packet_required": True,
            "both_structured_pass_required": True,
            "malformed_refusal_or_non_pass_fails_closed": True,
            "retry_or_tiebreaker_allowed": False,
            "scientific_result_mutable": False,
            "author_email_dispatch_requires_separate_human_approval": True,
        },
        "primary_pair": [
            {
                "event_id": row["event_id"],
                "reviewer_family": row["reviewer_family"],
                "canonical_model": row["canonical_model"],
                "declared_verdict": row["declared_verdict"],
                "validated_verdict": row["validated_verdict"],
                "structured_valid": row["validation_status"] == "completed_valid",
                "consensus_eligible": row["consensus_eligible"],
                "failure": row["failure"],
                "charged_cost_usd": row["charged_cost_usd"],
                "raw_response_sha256": row["trace"]["artifacts"]["raw_response"][
                    "sha256"
                ],
            }
            for row in primary
        ],
        "excluded_events": [
            {
                "event_id": "OR-REVIEW-20260801-003",
                "reason": (
                    "Additional GLM contract-recovery invocation occurred after the "
                    "primary pair and is ineligible under the no-retry rule."
                ),
                "declared_verdict": "PASS",
                "validated_verdict": "PASS",
                "charged_cost_usd": next(
                    row["charged_cost_usd"]
                    for row in events
                    if row["event_id"] == "OR-REVIEW-20260801-003"
                ),
            }
        ],
        "decision": "HARD_FAIL",
        "decision_reason": (
            "Neither primary-pair response was schema-valid: GLM returned PASS with "
            "the FAIL-only next step, and Kimi's JSON was truncated at the output "
            "limit. Both raw texts declared PASS, but the required two valid "
            "structured PASS decisions were not established."
        ),
        "publication_authorized": False,
        "human_review_required": True,
        "author_email_eligible_for_human_approval": False,
        "author_email_dispatch_authorized": False,
        "author_email_human_approval_required": True,
        "fable_resubmission_allowed": False,
        "supplemental_resubmission_allowed": False,
    }
    refusal_ledger = {
        "schema_version": "nulspec-fable-refusal-ledger-v1",
        "updated_at_utc": CONSENSUS_DECIDED_AT,
        "append_only": True,
        "totals": {
            "refusals": 1,
            "findings_returned": 0,
            "charged_cost_usd": fable_cost,
        },
        "refusals": [fable],
    }
    catalog_record = {
        "schema_version": "nulspec-supplemental-model-manifest-v1",
        "catalog_endpoint": "https://openrouter.ai/api/v1/models",
        "catalog_snapshot_sha256": CATALOG_SHA256,
        "catalog_snapshot_public": False,
        "catalog_entries_reverified_at_utc": CATALOG_REVERIFIED_AT,
        "selection_rule": "strongest current GLM and Kimi review models available",
        "models": list(MODELS.values()),
    }
    if catalog is not None:
        catalog_bytes = catalog.read_bytes()
        if sha256_bytes(catalog_bytes) != CATALOG_SHA256:
            raise ValueError("OpenRouter catalog snapshot hash changed")
        catalog_payload = json.loads(catalog_bytes)
        for expected in MODELS.values():
            row = next(
                item
                for item in catalog_payload["data"]
                if item["id"] == expected["requested_id"]
            )
            if row.get("canonical_slug") != expected["canonical_slug"]:
                raise ValueError("OpenRouter canonical slug changed")
            if sha256_bytes(canonical_bytes(row)) != expected["catalog_entry_sha256"]:
                raise ValueError("OpenRouter model entry hash changed")

    trace_lines = "".join(
        json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        + "\n"
        for row in traces
    )
    refusal_markdown = render_fable_refusals(refusal_ledger)
    external_markdown = render_external_ledger(ledger, consensus)
    consensus_markdown = render_consensus(consensus)
    outputs = {
        repo / "FABLE_REFUSALS.json": pretty(refusal_ledger),
        repo / "FABLE_REFUSALS.md": refusal_markdown,
        study / "results/external_review_ledger.json": pretty(ledger),
        study / "results/external_review_training_traces.jsonl": trace_lines,
        study / "results/supplemental_review_model_manifest.json": pretty(
            catalog_record
        ),
        study / "results/supplemental_review_consensus.json": pretty(consensus),
        study / "EXTERNAL_REVIEW_LEDGER.md": external_markdown,
        study / "SUPPLEMENTAL_REVIEW_CONSENSUS.md": consensus_markdown,
    }
    for path, content in outputs.items():
        assert_public_safe(str(path.relative_to(repo)), content)
    return outputs


def render_fable_refusals(ledger: dict[str, Any]) -> str:
    row = ledger["refusals"][0]
    quoted_provider_message = "\n".join(
        f"> {line}" if line else ">"
        for line in row["failure"]["provider_message_sanitized"].splitlines()
    )
    return f"""# Fable refusal ledger

This append-only ledger records technical or safeguard refusals before a
substantive NULSPEC peer review. Refusals are process evidence, not scientific
evidence about a paper or replication. Exact provider traces remain in the
private lab archive; this public record removes request/session identifiers and
machine-local context.

## {row["event_id"]}

- Study: `260723346` / arXiv `2607.23346v1`
- Attempt: {row["started_at_utc"]} to {row["completed_at_utc"]}
- Provider/model: Anthropic / `claude-fable-5`
- Category: `{row["failure"]["category"]}`
- Provider state: `{row["failure"]["stop_reason"]}` / `{row["failure"]["terminal_reason"]}`
- Findings returned: **0**
- Charged cost: **${row["charged_cost_usd"]:.6f}**
- Packet: `{PACKET_SHA256}` ({row["binding"]["packet_bytes"]:,} bytes)
- Prompt: `{PROMPT_SHA256}` ({row["binding"]["prompt_bytes"]:,} bytes)
- Raw response: `{row["trace"]["artifacts"]["raw_response"]["sha256"]}` ({row["trace"]["artifacts"]["raw_response"]["bytes"]:,} bytes)
- Publication consequence: {row["publication_consequence"]}

Sanitized provider message:

{quoted_provider_message}

### Cost components

| Served model | Input | Cache creation | Output | Cost (USD) |
|---|---:|---:|---:|---:|
| `claude-fable-5` | {row["model_usage"]["claude-fable-5"]["inputTokens"]:,} | {row["model_usage"]["claude-fable-5"]["cacheCreationInputTokens"]:,} | {row["model_usage"]["claude-fable-5"]["outputTokens"]:,} | ${row["model_usage"]["claude-fable-5"]["costUSD"]:.6f} |
| `claude-haiku-4-5-20251001` | {row["model_usage"]["claude-haiku-4-5-20251001"]["inputTokens"]:,} | {row["model_usage"]["claude-haiku-4-5-20251001"]["cacheCreationInputTokens"]:,} | {row["model_usage"]["claude-haiku-4-5-20251001"]["outputTokens"]:,} | ${row["model_usage"]["claude-haiku-4-5-20251001"]["costUSD"]:.6f} |
"""


def render_external_ledger(ledger: dict[str, Any], consensus: dict[str, Any]) -> str:
    rows = []
    for event in ledger["events"]:
        model = event.get("canonical_model") or event.get("model")
        verdict = event.get("validated_verdict") or "—"
        rows.append(
            f"| `{event['event_id']}` | {event['provider']} | `{model}` | "
            f"{event['validation_status']} | {verdict} | "
            f"${event['charged_cost_usd']:.8f} |"
        )
    return f"""# External peer-review ledger

Every provider request is retained, including zero-cost transport failures and
an ineligible extra call. The exact raw traces remain in the ignored immutable
lab archive. `results/external_review_training_traces.jsonl` is the sanitized,
public, training-ready projection; hashes and byte counts bind it to the exact
private originals.

## Accounting

- Anthropic/Fable: **${ledger["totals"]["anthropic_usd"]:.6f}**
- OpenRouter/GLM+Kimi: **${ledger["totals"]["openrouter_usd"]:.8f}**
- Total external-review cost: **${ledger["totals"]["total_usd"]:.8f}**
- Provider request events: **{ledger["totals"]["provider_request_events"]}**
- Actual model invocations: **{ledger["totals"]["model_invocations"]}**
- Consensus-eligible invocations: **{ledger["totals"]["consensus_eligible_model_invocations"]}**

| Event | Provider | Model | Validation | Validated verdict | Cost |
|---|---|---|---|---|---:|
{chr(10).join(rows)}

## Release consequence

The permitted GLM/Kimi pair did not produce two valid structured PASS
decisions. GLM's raw content declared PASS but paired it with the FAIL-only next
step; Kimi's raw content declared PASS but ended at the output limit before the
JSON completed. The later valid GLM recovery is retained and billed but cannot
count. The supplemental decision is therefore **{consensus["decision"]}** and
publication remains blocked for human review. No external review can authorize
author-email dispatch; that always requires separate approval of the exact
hashed draft.
"""


def render_consensus(consensus: dict[str, Any]) -> str:
    glm, kimi = consensus["primary_pair"]
    excluded = consensus["excluded_events"][0]
    return f"""# Supplemental GLM/Kimi review disposition

**Decision: {consensus["decision"]}**

This is the fail-closed disposition after Fable's one-shot safeguard refusal.
Both supplemental reviewers received the same immutable packet and prompt. To
substitute for a Fable PASS, both had to return independently schema-valid
`PASS` decisions. A refusal, malformed response, truncation, or non-PASS result
fails closed. There is no retry or tiebreaker.

| Reviewer | Exact model | Declared | Schema-valid | Consensus result | Cost |
|---|---|---:|---:|---:|---:|
| GLM | `{glm["canonical_model"]}` | {glm["declared_verdict"]} | {str(glm["structured_valid"]).lower()} | excluded | ${glm["charged_cost_usd"]:.8f} |
| Kimi | `{kimi["canonical_model"]}` | {kimi["declared_verdict"]} | {str(kimi["structured_valid"]).lower()} | excluded | ${kimi["charged_cost_usd"]:.8f} |

{consensus["decision_reason"]}

An additional GLM call later returned a valid PASS, but event
`{excluded["event_id"]}` is explicitly ineligible because it occurred after the
primary pair. Its **${excluded["charged_cost_usd"]:.8f}** cost and full trace are
still retained.

## Gates

- Publication authorized: `false`
- Human review required: `true`
- Fable resubmission: `forbidden`
- Supplemental resubmission: `forbidden`
- Author email eligible for human approval: `false`
- Author email dispatch authorized: `false`
- Separate final human email approval remains mandatory: `true`

The reviewer outcomes do not change the frozen scientific classification or
any experimental result.
"""


def verify_public(outputs: dict[Path, str]) -> None:
    for path, expected in outputs.items():
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = path.read_text()
        if actual != expected:
            raise ValueError(f"public review artifact differs: {path}")
        assert_public_safe(str(path), actual)
    ledger = json.loads(
        next(
            content
            for path, content in outputs.items()
            if path.name == "external_review_ledger.json"
        )
    )
    consensus = json.loads(
        next(
            content
            for path, content in outputs.items()
            if path.name == "supplemental_review_consensus.json"
        )
    )
    if ledger["totals"]["total_usd"] != 4.44176232:
        raise ValueError("external-review total changed")
    if consensus["decision"] != "HARD_FAIL":
        raise ValueError("actual supplemental disposition must fail closed")
    if consensus["publication_authorized"] is not False:
        raise ValueError("supplemental disposition opened publication")
    if consensus["author_email_dispatch_authorized"] is not False:
        raise ValueError("supplemental disposition opened email dispatch")
    traces = (
        (outputs_path(outputs, "external_review_training_traces.jsonl"))
        .read_text()
        .splitlines()
    )
    if len(traces) != 6:
        raise ValueError("sanitized training trace count changed")
    if [json.loads(line)["event_id"] for line in traces] != [
        row["event_id"] for row in ledger["events"]
    ]:
        raise ValueError("training traces differ from ledger chronology")


def outputs_path(outputs: dict[Path, str], name: str) -> Path:
    return next(path for path in outputs if path.name == name)


def main() -> int:
    args = parse_args()
    study = args.study_root.resolve()
    outputs = build_payloads(study, args.catalog.resolve() if args.catalog else None)
    if args.mode == "build":
        for path, content in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        print(
            "EXTERNAL_REVIEW_AUDIT_BUILT "
            f"files={len(outputs)} total_usd=4.44176232 consensus=HARD_FAIL"
        )
    verify_public(outputs)
    print(
        "EXTERNAL_REVIEW_AUDIT_PASS "
        f"files={len(outputs)} total_usd=4.44176232 consensus=HARD_FAIL"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
