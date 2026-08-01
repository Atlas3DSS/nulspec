#!/usr/bin/env python3
"""Audit Qwen with independent GLM and Kimi teachers, then use Codex.

The one-way boundary is inherited from ``outer_teacher.py``: GLM, Kimi, and
Codex receive Qwen reviewer records, never the underlying policy outputs,
prompts, checkpoints, rewards, or training state. Every invocation attempt is
immutable and trace-complete. Fable is deliberately excluded from this
recurring teacher loop and reserved for separate final-release review and one
bounded critique after the pipeline is complete.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import time
from typing import Any

try:
    from extension.direct_teacher_providers import (
        FIRST_EVENT_TIMEOUT_SECONDS,
        STREAM_IDLE_TIMEOUT_SECONDS,
        TOTAL_RESPONSE_TIMEOUT_SECONDS,
        ProviderRoute,
        ProviderStreamError,
        available_completion_tokens,
        build_stream_payload,
        normalized_usage,
        route_count,
        route_for,
        stream_chat_completion,
    )
    from extension.outer_teacher import ALLOWED_RECORD_FIELDS
except ModuleNotFoundError:  # Direct execution from the repository root.
    from direct_teacher_providers import (
        FIRST_EVENT_TIMEOUT_SECONDS,
        STREAM_IDLE_TIMEOUT_SECONDS,
        TOTAL_RESPONSE_TIMEOUT_SECONDS,
        ProviderRoute,
        ProviderStreamError,
        available_completion_tokens,
        build_stream_payload,
        normalized_usage,
        route_count,
        route_for,
        stream_chat_completion,
    )
    from outer_teacher import ALLOWED_RECORD_FIELDS


TRACE_SCHEMA = "nulspec-qwen-review-hierarchy-trace-v2"
PUBLIC_SCHEMA = "nulspec-qwen-review-hierarchy-public-v2"
DEFAULT_TEACHERS = ("z-ai/glm-5.2", "moonshotai/kimi-k3")
QWEN_SCOPE = "qwen_records_only"
CODEX_SCOPE = "qwen_records_and_outer_teacher_audits_only"
MAX_TEACHER_ATTEMPTS = 3
MAX_CODEX_ATTEMPTS = 3
EVENT_LOG_LOCK = threading.Lock()


class ReviewHierarchyError(RuntimeError):
    """Raised when a trace, scope, provider, or structured-output gate fails."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def encoded_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def write_new_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(value)


def write_new_json(path: Path, value: Any) -> None:
    write_new_bytes(path, encoded_json(value))


def append_event(path: Path, event: str, **fields: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"at_utc": now(), "event": event, **fields}
    with EVENT_LOG_LOCK:
        with path.open("ab") as handle:
            handle.write(json.dumps(record, sort_keys=True).encode() + b"\n")


def sanitize_failure_message(value: str) -> str:
    """Remove account-specific URLs and identifiers from public failures."""

    value = re.sub(
        r"https://openrouter\.ai/[^\s\"']+",
        "[OpenRouter account URL redacted]",
        value,
    )
    value = re.sub(r"user_[A-Za-z0-9_-]+", "[OpenRouter user ID redacted]", value)
    return value


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ReviewHierarchyError(f"expected a JSON object: {path}")
    return value


def validate_qwen_packet(packet: dict[str, Any]) -> None:
    if set(packet) != {"protocol", "pairs"}:
        raise ReviewHierarchyError("Qwen packet has unexpected top-level fields")
    protocol = packet.get("protocol")
    pairs = packet.get("pairs")
    if not isinstance(protocol, dict) or not isinstance(pairs, list) or not pairs:
        raise ReviewHierarchyError("Qwen packet is incomplete")
    boundary = str(protocol.get("boundary", "")).lower()
    if "only qwen reviewer records" not in boundary:
        raise ReviewHierarchyError("Qwen-only evidence boundary is not declared")
    seen: set[tuple[str, str]] = set()
    for pair in pairs:
        if not isinstance(pair, dict) or set(pair) != {
            "label",
            "pair_id",
            "selection_reason",
            "qwen_reviews",
        }:
            raise ReviewHierarchyError("Qwen packet pair has unexpected fields")
        label = pair.get("label")
        pair_id = pair.get("pair_id")
        reviews = pair.get("qwen_reviews")
        if not isinstance(label, str) or not isinstance(pair_id, str):
            raise ReviewHierarchyError("Qwen packet pair identity is invalid")
        if (label, pair_id) in seen:
            raise ReviewHierarchyError("Qwen packet contains a duplicate pair")
        seen.add((label, pair_id))
        if not isinstance(reviews, list) or not reviews:
            raise ReviewHierarchyError("Qwen packet pair has no reviews")
        for review in reviews:
            if not isinstance(review, dict) or not set(review).issubset(
                ALLOWED_RECORD_FIELDS
            ):
                raise ReviewHierarchyError("Qwen review crossed the field boundary")
            if "qwen" not in str(review.get("model", "")).lower():
                raise ReviewHierarchyError("packet contains a non-Qwen primary review")
            if review.get("label") != label or review.get("pair_id") != pair_id:
                raise ReviewHierarchyError(
                    "Qwen review identity does not match its pair"
                )


def model_directory(model_id: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", model_id.lower()).strip("-")
    if not value:
        raise ReviewHierarchyError("model ID cannot form a trace directory")
    return value


def parse_teacher_content(content: str) -> dict[str, Any]:
    """Parse the final streamed content without repairing its scientific answer."""

    if not content.strip():
        raise ReviewHierarchyError("outer teacher returned no content")
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1])
            if text.lstrip().startswith("json"):
                text = text.lstrip()[4:].lstrip()
    result = json.loads(text)
    if not isinstance(result, dict):
        raise ReviewHierarchyError("outer-teacher result is not a JSON object")
    return result


def validate_teacher_audit(audit: dict[str, Any], packet: dict[str, Any]) -> list[str]:
    expected_fields = {
        "scope_confirmation",
        "overall_assessment",
        "reviewer_reliability",
        "findings",
        "systemic_patterns",
        "summary",
    }
    if set(audit) != expected_fields:
        raise ReviewHierarchyError(
            "outer teacher returned unexpected or missing audit fields"
        )
    if audit.get("scope_confirmation") != QWEN_SCOPE:
        raise ReviewHierarchyError("outer teacher failed the Qwen-only scope gate")
    if audit.get("overall_assessment") not in {"pass", "warn", "fail"}:
        raise ReviewHierarchyError("outer teacher returned an invalid assessment")
    reliability = audit.get("reviewer_reliability")
    if not isinstance(reliability, (int, float)) or not 0 <= reliability <= 1:
        raise ReviewHierarchyError("outer teacher returned invalid reliability")
    findings = audit.get("findings")
    if not isinstance(findings, list):
        raise ReviewHierarchyError("outer teacher findings are not an array")
    systemic = audit.get("systemic_patterns")
    if not isinstance(systemic, list) or not all(
        isinstance(value, str) for value in systemic
    ):
        raise ReviewHierarchyError("outer teacher systemic patterns are invalid")
    if not isinstance(audit.get("summary"), str):
        raise ReviewHierarchyError("outer teacher summary is invalid")
    valid_pairs = {(pair["label"], pair["pair_id"]) for pair in packet["pairs"]}
    warnings = []
    for finding in findings:
        if not isinstance(finding, dict) or set(finding) != {
            "pair_id",
            "label",
            "severity",
            "issue",
            "rationale",
            "recommended_action",
        }:
            raise ReviewHierarchyError("outer teacher returned a malformed finding")
        if finding.get("severity") not in {"info", "warning", "critical"}:
            raise ReviewHierarchyError("outer teacher returned invalid severity")
        if not all(
            isinstance(finding.get(field), str)
            for field in (
                "pair_id",
                "label",
                "issue",
                "rationale",
                "recommended_action",
            )
        ):
            raise ReviewHierarchyError("outer teacher finding fields are invalid")
        identity = (finding.get("label"), finding.get("pair_id"))
        if identity not in valid_pairs:
            warnings.append(
                f"finding_cited_pair_outside_packet:{identity[0]}:{identity[1]}"
            )
    return warnings


def high_depth_harness(
    model_id: str,
    packet: dict[str, Any],
    route: ProviderRoute,
) -> dict[str, Any]:
    packet_text = json.dumps(packet, indent=2, sort_keys=True)
    delimiter = "qwen_review_packet"
    if f"<{delimiter}>" in packet_text or f"</{delimiter}>" in packet_text:
        raise ReviewHierarchyError("Qwen packet collides with prompt delimiters")
    common = (
        "Audit the Qwen primary review process, not the unseen candidate content. "
        "Check order consistency, winner/rationale contradictions, unsupported "
        "certainty, malformed or vacuous reasoning, and systemic position bias. "
        "Opposite raw A/B winners can be correct when mapped_winner agrees. Do not "
        "infer missing prompts or candidate outputs. Do not optimize for agreement "
        "with another reviewer. Findings are process-audit flags only: they cannot "
        "become training reward, alter the primary estimate, authorize publication, "
        "or authorize an external message. Return exactly one JSON object matching "
        "the response schema and set scope_confirmation to qwen_records_only."
    )
    if model_id.startswith("z-ai/glm-"):
        profile = "glm-qwen-outer-teacher-high-reasoning-max-output-direct-v3"
        system = (
            "You are GLM acting as an independent outer teacher in a scientific "
            "review hierarchy. Examine the complete reference packet inside XML "
            "tags before deciding. Think deeply, cite exact pair labels and IDs, "
            "and return no prose outside the structured JSON. " + common
        )
    elif model_id.startswith("moonshotai/kimi-"):
        profile = "kimi-qwen-outer-teacher-high-reasoning-max-output-direct-v3"
        system = (
            "You are Kimi acting as an independent outer teacher in a scientific "
            "review hierarchy. Internally complete these steps before responding: "
            "(1) inspect population summaries, (2) inspect every selected pair in "
            "both orientations, (3) separate mapped-winner consistency from raw "
            "position preference, (4) check every finding against an exact pair, "
            "and (5) validate the final JSON. Return no Markdown or preface. " + common
        )
    else:
        raise ReviewHierarchyError(
            f"teacher loop accepts GLM and Kimi only, not {model_id}"
        )
    user = f"<{delimiter}>\n{packet_text}\n</{delimiter}>"
    max_tokens, max_tokens_basis = available_completion_tokens(route, system, user)
    return {
        "profile": profile,
        "system_prompt": system,
        "user_prompt": user,
        "request_parameters": {
            route.max_tokens_field: max_tokens,
            **route.reasoning_parameters,
            **route.request_parameters,
        },
        "max_tokens_basis": max_tokens_basis,
    }


def run_outer_teacher_attempt(
    model_id: str,
    attempt_id: str,
    provider_keys: dict[str, str],
    packet: dict[str, Any],
    schema: dict[str, Any],
    trace_root: Path,
    event_log: Path,
    attempt_number: int,
    repair: dict[str, Any] | None,
) -> dict[str, Any]:
    family = "GLM" if model_id.startswith("z-ai/glm-") else "Kimi"
    overrides = (repair or {}).get("parameter_overrides") or {}
    route_index = int(overrides.get("route_index", 0))
    route = route_for(model_id, route_index)
    directory = (
        trace_root
        / "outer-teachers"
        / model_directory(model_id)
        / f"attempt-{attempt_number:02d}"
    )
    directory.mkdir(parents=True, exist_ok=False)
    started_at = now()
    append_event(
        event_log,
        "outer_teacher_started",
        attempt_id=attempt_id,
        attempt_number=attempt_number,
        model_id=model_id,
        provider_route_id=route.route_id,
        repair_of_attempt_id=(repair.get("repair_of_attempt_id") if repair else None),
    )
    public: dict[str, Any] = {
        "attempt_id": attempt_id,
        "attempt_number": attempt_number,
        "reviewer_family": family,
        "requested_model_id": model_id,
        "status": "setup_failed",
        "started_at_utc": started_at,
        "invocation_count": 0,
        "model_invocation_count": 0,
        "retry_allowed": False,
        "decision_weight": 0,
        "provider_route_index": route_index,
        "provider_route": route.public_record(),
        "first_event_timeout_seconds": FIRST_EVENT_TIMEOUT_SECONDS,
        "stream_idle_timeout_seconds": STREAM_IDLE_TIMEOUT_SECONDS,
        "total_response_timeout_seconds": TOTAL_RESPONSE_TIMEOUT_SECONDS,
        "linked_repair_allowed": attempt_number < MAX_TEACHER_ATTEMPTS,
        "repair_of_attempt_id": (
            repair.get("repair_of_attempt_id") if repair else None
        ),
        "repair_action": repair,
    }

    def record_response_headers(metadata: dict[str, Any]) -> None:
        headers = metadata.pop("response_headers", None)
        if isinstance(headers, dict):
            header_bytes = encoded_json(headers)
            path = directory / "response-headers.json"
            if not path.exists():
                write_new_bytes(path, header_bytes)
            public["response_headers_byte_count"] = len(header_bytes)
            public["response_headers_sha256"] = sha256_bytes(header_bytes)

    try:
        provider_key = provider_keys.get(route.key_env, "").strip()
        if (
            len(provider_key) >= 2
            and provider_key[0] == provider_key[-1]
            and provider_key[0] in {"'", '"'}
        ):
            provider_key = provider_key[1:-1]
        if len(provider_key) < 8:
            raise ReviewHierarchyError(
                f"{route.key_env} is missing for {route.route_id}"
            )
        harness = high_depth_harness(model_id, packet, route)
        system = harness["system_prompt"]
        user = harness["user_prompt"]
        max_tokens = int(harness["request_parameters"][route.max_tokens_field])
        if repair:
            if "max_tokens" in overrides:
                max_tokens = int(overrides["max_tokens"])
            system += (
                " This is a linked reissue because an earlier invocation ended "
                "without a valid audit. Audit the immutable packet independently "
                "from the beginning; no prior scientific answer has been accepted."
            )
        payload = build_stream_payload(route, system, user, schema, max_tokens)
        transmitted_system = payload["messages"][0]["content"]
        transmitted_user = payload["messages"][1]["content"]
        parameters = {
            parameter_name: value
            for parameter_name, value in payload.items()
            if parameter_name not in {"model", "messages", "response_format"}
        }
        write_new_bytes(directory / "system-prompt.txt", transmitted_system.encode())
        write_new_bytes(directory / "user-prompt.txt", transmitted_user.encode())
        request_bytes = encoded_json(payload)
        write_new_bytes(directory / "request.json", request_bytes)
        route_record = route.public_record()
        route_hash = sha256_bytes(encoded_json(route_record))
        write_new_json(
            directory / "attempt-start.json",
            {
                "schema_version": TRACE_SCHEMA,
                "attempt_id": attempt_id,
                "started_at_utc": started_at,
                "model_id": model_id,
                "provider_model_id": route.provider_model_id,
                "provider_route_index": route_index,
                "provider_route": route_record,
                "provider_route_sha256": route_hash,
                "packet_sha256": sha256_bytes(encoded_json(packet)),
                "system_prompt_sha256": sha256_bytes(transmitted_system.encode()),
                "user_prompt_sha256": sha256_bytes(transmitted_user.encode()),
                "request_byte_count": len(request_bytes),
                "request_sha256": sha256_bytes(request_bytes),
                "harness_profile": harness["profile"],
                "request_parameters": parameters,
                "first_event_timeout_seconds": FIRST_EVENT_TIMEOUT_SECONDS,
                "stream_idle_timeout_seconds": STREAM_IDLE_TIMEOUT_SECONDS,
                "total_response_timeout_seconds": TOTAL_RESPONSE_TIMEOUT_SECONDS,
                "max_tokens_basis": harness["max_tokens_basis"],
                "planned_model_invocation_count": 1,
                "retry_allowed": False,
                "linked_repair_allowed": attempt_number < MAX_TEACHER_ATTEMPTS,
                "repair_of_attempt_id": public["repair_of_attempt_id"],
                "repair_action": repair,
            },
        )
        public.update(
            {
                "status": "invoked_invalid",
                "canonical_slug": route.provider_model_id,
                "provider_model_id": route.provider_model_id,
                "provider_route_sha256": route_hash,
                "provider_context_length": route.context_length,
                "provider_max_completion_tokens": route.max_completion_tokens,
                "harness_profile": harness["profile"],
                "request_parameters": parameters,
                "max_tokens_basis": harness["max_tokens_basis"],
                "system_prompt_sha256": sha256_bytes(transmitted_system.encode()),
                "user_prompt_sha256": sha256_bytes(transmitted_user.encode()),
                "request_byte_count": len(request_bytes),
                "request_sha256": sha256_bytes(request_bytes),
                "invocation_count": 1,
                "model_invocation_count": 1,
            }
        )
        response = stream_chat_completion(
            route,
            provider_key,
            payload,
            directory / "raw-response.sse",
            directory / "stream-events.jsonl",
        )
        record_response_headers(response)
        content = response.pop("content")
        reasoning_content = response.pop("reasoning_content")
        usage = response.pop("usage")
        public.update(
            {
                "completed_at_utc": now(),
                **response,
                "content_byte_count": len(content.encode()),
                "content_sha256": sha256_bytes(content.encode()),
                "reasoning_byte_count": len(reasoning_content.encode()),
                "reasoning_sha256": sha256_bytes(reasoning_content.encode()),
            }
        )
        write_new_json(
            directory / "assembled-response.json",
            {
                "provider_model": response.get("response_model"),
                "finish_reason": response.get("finish_reason"),
                "content": content,
                "reasoning_content": reasoning_content,
                "usage": usage,
            },
        )
        public["usage"] = normalized_usage(route, usage)
        audit = parse_teacher_content(content)
        contract_warnings = validate_teacher_audit(audit, packet)
        write_new_json(directory / "parsed-audit.json", audit)
        public["status"] = "completed_valid"
        public["decision_weight"] = 1
        public["contract_warnings"] = contract_warnings
        public["audit"] = audit
    except ProviderStreamError as error:
        metadata = json.loads(json.dumps(error.metadata))
        record_response_headers(metadata)
        public.update(metadata)
        failure = f"{type(error).__name__}: {error}"
        write_new_bytes(directory / "failure.txt", failure.encode())
        public["failure"] = sanitize_failure_message(failure)
        public["failure_sha256"] = sha256_bytes(failure.encode())
        public.setdefault("completed_at_utc", now())
    except Exception as error:
        failure = f"{type(error).__name__}: {error}"
        write_new_bytes(directory / "failure.txt", failure.encode())
        public["failure"] = sanitize_failure_message(failure)
        public["failure_sha256"] = sha256_bytes(failure.encode())
        public.setdefault("completed_at_utc", now())
    for field_prefix, filename in (
        ("raw_response", "raw-response.sse"),
        ("stream_events", "stream-events.jsonl"),
        ("assembled_response", "assembled-response.json"),
        ("parsed_audit", "parsed-audit.json"),
    ):
        path = directory / filename
        if path.is_file():
            raw = path.read_bytes()
            public[f"{field_prefix}_byte_count"] = len(raw)
            public[f"{field_prefix}_sha256"] = sha256_bytes(raw)
    write_new_json(directory / "attempt-complete.json", public)
    append_event(
        event_log,
        "outer_teacher_completed",
        attempt_id=attempt_id,
        attempt_number=attempt_number,
        model_id=model_id,
        status=public["status"],
    )
    return public


def repair_plan_for_attempt(attempt: dict[str, Any]) -> dict[str, Any]:
    """Describe the next immutable attempt after an invalid invocation."""

    failure = str(attempt.get("failure") or "")
    model_id = str(attempt.get("requested_model_id") or "")
    current_route = int(attempt.get("provider_route_index") or 0)
    count = route_count(model_id)
    next_route = (current_route + 1) % count if count else current_route
    repair: dict[str, Any] = {
        "repair_of_attempt_id": attempt["attempt_id"],
        "kind": "reissue_after_invalid_invocation",
        "diagnosis": failure,
        "parameter_overrides": {},
    }
    reroute = {"route_index": next_route} if count > 1 else {}
    lower_failure = failure.lower()
    if attempt.get("http_status") == 402:
        repair["kind"] = "reissue_after_billing_failure_with_provider_reroute"
        repair["diagnosis"] = (
            "The direct provider rejected the request for account or billing "
            "reasons; the model did not return an audit."
        )
        repair["parameter_overrides"] = reroute
    elif "timed out" in lower_failure or "timeout" in lower_failure:
        repair["kind"] = "reissue_after_stream_timeout_with_provider_reroute"
        repair["diagnosis"] = (
            "The direct provider did not maintain a valid progress stream within "
            "the first-event, idle, or total response deadline."
        )
        repair["parameter_overrides"] = reroute
    elif attempt.get("http_status") in {408, 409, 425, 429, 500, 502, 503, 504}:
        repair["kind"] = "reissue_after_transient_failure_with_provider_reroute"
        repair["parameter_overrides"] = reroute
    elif " is missing for " in failure:
        if model_id.startswith("moonshotai/kimi-") and current_route > 0:
            repair["kind"] = "block_after_missing_independent_fallback_key"
            repair["diagnosis"] = (
                "The configured independent Kimi fallback has no funded key. "
                "The chain must block rather than rotate back to the primary route."
            )
            repair["terminal_without_reissue"] = True
        else:
            repair["kind"] = "reissue_after_missing_provider_key_with_reroute"
            repair["parameter_overrides"] = reroute
    elif any(value in lower_failure for value in ("json", "schema", "content")):
        repair["kind"] = "reissue_after_structured_output_failure"
        repair["diagnosis"] = (
            "The provider returned a response, but its final answer did not pass "
            "the JSON and audit contract. The failed output remains preserved."
        )
    elif "providerstreamerror" in lower_failure:
        repair["kind"] = "reissue_after_transport_failure_with_provider_reroute"
        repair["parameter_overrides"] = reroute
    return repair


def run_teacher_with_repairs(
    model_id: str,
    run_id: str,
    provider_keys: dict[str, str],
    packet: dict[str, Any],
    schema: dict[str, Any],
    trace_root: Path,
    event_log: Path,
) -> dict[str, Any]:
    """Run one logical teacher until valid or the repair budget is exhausted."""

    family = "GLM" if model_id.startswith("z-ai/glm-") else "Kimi"
    chain_started = now()
    attempts: list[dict[str, Any]] = []
    repair: dict[str, Any] | None = None
    blocked_repair: dict[str, Any] | None = None
    for attempt_number in range(1, MAX_TEACHER_ATTEMPTS + 1):
        attempt_id = f"{run_id}-{family.upper()}-A{attempt_number}"
        attempt = run_outer_teacher_attempt(
            model_id,
            attempt_id,
            provider_keys,
            packet,
            schema,
            trace_root,
            event_log,
            attempt_number,
            repair,
        )
        attempts.append(attempt)
        if attempt["status"] == "completed_valid":
            break
        if attempt_number < MAX_TEACHER_ATTEMPTS:
            repair = repair_plan_for_attempt(attempt)
            if repair.get("terminal_without_reissue") is True:
                blocked_repair = repair
                write_new_json(
                    trace_root
                    / "outer-teachers"
                    / model_directory(model_id)
                    / f"repair-blocked-after-{attempt_number:02d}.json",
                    repair,
                )
                append_event(
                    event_log,
                    "outer_teacher_repair_blocked",
                    reviewer_family=family,
                    failed_attempt_id=attempt_id,
                    repair_kind=repair["kind"],
                )
                break
            append_event(
                event_log,
                "outer_teacher_repair_scheduled",
                reviewer_family=family,
                failed_attempt_id=attempt_id,
                next_attempt_number=attempt_number + 1,
                repair_kind=repair["kind"],
            )

    terminal = attempts[-1]
    completed = terminal["status"] == "completed_valid"
    chain = {
        "teacher_id": f"{run_id}-{family.upper()}",
        "reviewer_family": family,
        "requested_model_id": model_id,
        "execution_mode": "parallel_independent",
        "status": (
            "completed_valid"
            if completed
            else (
                "blocked_no_configured_fallback"
                if blocked_repair is not None
                else "repair_exhausted"
            )
        ),
        "started_at_utc": chain_started,
        "completed_at_utc": now(),
        "attempt_count": len(attempts),
        "repair_count": len(attempts) - 1,
        "maximum_attempts": MAX_TEACHER_ATTEMPTS,
        "terminal_attempt_id": terminal["attempt_id"],
        "terminal_audit": terminal.get("audit"),
        "terminal_block": blocked_repair,
        "attempts": attempts,
        "reported_cost_usd": sum(
            float((attempt.get("usage") or {}).get("cost") or 0) for attempt in attempts
        ),
    }
    write_new_json(
        trace_root
        / "outer-teachers"
        / model_directory(model_id)
        / "chain-complete.json",
        chain,
    )
    append_event(
        event_log,
        "outer_teacher_chain_completed",
        reviewer_family=family,
        status=chain["status"],
        attempt_count=chain["attempt_count"],
        repair_count=chain["repair_count"],
    )
    return chain


def run_parallel_teachers(
    teachers: tuple[str, ...],
    run_id: str,
    provider_keys: dict[str, str],
    packet: dict[str, Any],
    schema: dict[str, Any],
    trace_root: Path,
    event_log: Path,
) -> list[dict[str, Any]]:
    """Fan GLM and Kimi out concurrently and preserve deterministic join order."""

    append_event(
        event_log,
        "parallel_outer_teachers_started",
        model_ids=list(teachers),
    )
    with ThreadPoolExecutor(
        max_workers=2, thread_name_prefix="nulspec-teacher"
    ) as pool:
        futures = {
            model_id: pool.submit(
                run_teacher_with_repairs,
                model_id,
                run_id,
                provider_keys,
                packet,
                schema,
                trace_root,
                event_log,
            )
            for model_id in teachers
        }
        chains = [futures[model_id].result() for model_id in teachers]
    append_event(
        event_log,
        "parallel_outer_teachers_joined",
        statuses={chain["reviewer_family"]: chain["status"] for chain in chains},
    )
    return chains


def codex_packet(
    qwen_packet: dict[str, Any], teacher_attempts: list[dict[str, Any]]
) -> dict[str, Any]:
    projected = json.loads(json.dumps(teacher_attempts))
    for attempt in projected:
        attempt["model_id"] = attempt["requested_model_id"]
    return {
        "protocol": {
            "name": "qwen-glm-kimi-codex-review-hierarchy-v2",
            "boundary": (
                "Contains only the sanitized Qwen reviewer packet and complete "
                "credential-free attempt records for the independent GLM and "
                "Kimi audits of that packet."
            ),
            "trace_evidence_boundary": (
                "Raw SSE and normalized event bodies remain in the ignored trace "
                "archive. Each attempt record binds those files, the request, "
                "response headers, assembled response, and parsed audit by byte "
                "count and SHA-256. Their bodies are intentionally not duplicated "
                "into this adjudication packet. End-to-end hash validation occurs "
                "after Codex completes."
            ),
            "authority": (
                "Codex adjudicates the process audit but cannot alter training "
                "reward, rewrite the primary result, authorize publication, or "
                "authorize external messaging."
            ),
            "excluded_reviewer": (
                "Fable is not part of the recurring teacher loop. It is reserved "
                "for final-release review and one completed-pipeline critique."
            ),
        },
        "qwen_primary_packet": qwen_packet,
        "outer_teacher_attempts": projected,
    }


def outer_outer_prompt(packet: dict[str, Any]) -> str:
    return (
        "You are Codex acting as the outer adjudicator in a scientific review "
        "hierarchy: local Qwen primary reviewer, independent GLM and Kimi outer "
        "teachers, then Codex.\n\n"
        "HARD SCOPE BOUNDARY:\n"
        "- Review only the supplied Qwen packet and GLM/Kimi audit records.\n"
        "- Fable is intentionally excluded from this recurring teacher loop; do "
        "not request, infer, or simulate a Fable review.\n"
        "- Do not infer or invent underlying prompts, policy outputs, checkpoints, "
        "rewards, or training state.\n"
        "- Evaluate each teacher independently before comparing them.\n"
        "- Preserve disagreements explicitly; agreement is not proof and model "
        "variants are not independent replications.\n"
        "- A missing or malformed response is a trace finding, not a vote.\n"
        "- Each credential-free attempt record includes the route, response model, "
        "timing, usage, cost, and hashes/counts binding its archived raw evidence. "
        "Raw SSE bodies are deliberately not duplicated here; do not call them "
        "missing when their trace metadata is complete. Do not claim to have "
        "independently recomputed those hashes.\n"
        "- Contract warnings must remain visible and must not be silently repaired.\n"
        "- You may adjudicate whether this process audit is usable. You cannot "
        "alter training reward, rewrite the primary result, authorize publication, "
        "or authorize external messaging.\n"
        "- Apply the same factual, charitable standard to NULSPEC integration "
        "failures and external failures. Do not mock any party.\n\n"
        "Return JSON matching the supplied schema. Set scope_confirmation exactly "
        "to qwen_records_and_outer_teacher_audits_only. Include one teacher "
        "assessment for every attempt using its exact attempt_id and model_id. For "
        "pair-specific findings, copy pair_id and label exactly; otherwise use null "
        "for both. Cite packet fields or teacher attempt IDs in every evidence "
        "reference. All automatic release and training controls must remain false.\n\n"
        "REVIEW HIERARCHY PACKET:\n" + json.dumps(packet, indent=2, sort_keys=True)
    )


def validate_outer_outer(decision: dict[str, Any], packet: dict[str, Any]) -> list[str]:
    if decision.get("scope_confirmation") != CODEX_SCOPE:
        raise ReviewHierarchyError("Codex failed the outer scope gate")
    controls = decision.get("release_control")
    if controls != {
        "automatic_publication_authorized": False,
        "automatic_training_signal_authorized": False,
        "author_email_dispatch_authorized": False,
    }:
        raise ReviewHierarchyError("Codex returned invalid release controls")
    expected_attempts = {
        (row["attempt_id"], row["model_id"]) for row in packet["outer_teacher_attempts"]
    }
    assessments = decision.get("teacher_assessments")
    if (
        not isinstance(assessments, list)
        or {
            (row.get("attempt_id"), row.get("model_id"))
            for row in assessments
            if isinstance(row, dict)
        }
        != expected_attempts
    ):
        raise ReviewHierarchyError("Codex did not assess every outer-teacher attempt")
    valid_pairs = {
        (row["label"], row["pair_id"]) for row in packet["qwen_primary_packet"]["pairs"]
    }
    warnings = []
    for finding in decision.get("findings", []):
        pair_id = finding.get("pair_id")
        label = finding.get("label")
        if (pair_id is None) != (label is None):
            raise ReviewHierarchyError("Codex finding has a partial pair identity")
        if pair_id is not None and (label, pair_id) not in valid_pairs:
            warnings.append(f"finding_cited_pair_outside_packet:{label}:{pair_id}")
    return warnings


def run_codex_outer_outer_attempt(
    packet: dict[str, Any],
    schema_path: Path,
    directory: Path,
    event_log: Path,
    model: str | None,
    attempt_id: str,
    attempt_number: int,
    repair: dict[str, Any] | None,
) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=False)
    prompt = outer_outer_prompt(packet)
    if repair:
        prompt += (
            "\n\nLINKED CONTRACT REISSUE:\n"
            "The previous Codex invocation is preserved unchanged and was not "
            "accepted because its structured adjudication failed this gate: "
            f"{repair['diagnosis']}\n"
            "Adjudicate the immutable packet again. Return a new complete object; "
            "do not edit or quote the prior output. For every finding, pair_id and "
            "label must either both be null or both identify the same supplied "
            "Qwen pair."
        )
    output_path = directory / "last-message.json"
    write_new_bytes(directory / "prompt.txt", prompt.encode())
    version = subprocess.run(
        ["codex", "--version"], text=True, capture_output=True, check=False
    )
    write_new_bytes(directory / "codex-version.txt", version.stdout.encode())
    command = [
        "codex",
        "exec",
        "--ephemeral",
        "--sandbox",
        "read-only",
        "--skip-git-repo-check",
        "--ignore-user-config",
        "--ignore-rules",
        "--json",
        "--color",
        "never",
        "--output-schema",
        str(schema_path.resolve()),
        "--output-last-message",
        str(output_path.resolve()),
    ]
    if model:
        command.extend(["--model", model])
    append_event(
        event_log,
        "outer_adjudicator_attempt_started",
        attempt_id=attempt_id,
        attempt_number=attempt_number,
        repair_of_attempt_id=(repair.get("repair_of_attempt_id") if repair else None),
    )
    started_at = now()
    with tempfile.TemporaryDirectory(prefix="nulspec-outer-codex-") as isolated:
        command.extend(["--cd", isolated, "-"])
        write_new_json(
            directory / "attempt-start.json",
            {
                "schema_version": TRACE_SCHEMA,
                "attempt_id": attempt_id,
                "attempt_number": attempt_number,
                "started_at_utc": started_at,
                "prompt_sha256": sha256_bytes(prompt.encode()),
                "schema_sha256": sha256_bytes(schema_path.read_bytes()),
                "codex_cli_version": version.stdout.strip(),
                "requested_model": model,
                "invocation_count": 1,
                "retry_allowed": False,
                "linked_repair_allowed": attempt_number < MAX_CODEX_ATTEMPTS,
                "repair_of_attempt_id": (
                    repair.get("repair_of_attempt_id") if repair else None
                ),
                "repair_action": repair,
            },
        )
        environment = os.environ.copy()
        environment.pop("OPENAI_API_KEY", None)
        environment.pop("CODEX_API_KEY", None)
        start = time.monotonic()
        result = subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            check=False,
            env=environment,
        )
        elapsed = round(time.monotonic() - start, 6)
    write_new_bytes(directory / "stdout.jsonl", result.stdout.encode())
    write_new_bytes(directory / "stderr.txt", result.stderr.encode())
    public: dict[str, Any] = {
        "attempt_id": attempt_id,
        "attempt_number": attempt_number,
        "status": "completed_invalid",
        "started_at_utc": started_at,
        "completed_at_utc": now(),
        "elapsed_seconds": elapsed,
        "return_code": result.returncode,
        "requested_model": model,
        "codex_cli_version": version.stdout.strip(),
        "prompt_sha256": sha256_bytes(prompt.encode()),
        "stdout_byte_count": len(result.stdout.encode()),
        "stdout_sha256": sha256_bytes(result.stdout.encode()),
        "stderr_byte_count": len(result.stderr.encode()),
        "stderr_sha256": sha256_bytes(result.stderr.encode()),
        "invocation_count": 1,
        "retry_allowed": False,
        "linked_repair_allowed": attempt_number < MAX_CODEX_ATTEMPTS,
        "repair_of_attempt_id": (
            repair.get("repair_of_attempt_id") if repair else None
        ),
        "repair_action": repair,
    }
    if output_path.is_file():
        public["last_message_byte_count"] = output_path.stat().st_size
        public["last_message_sha256"] = sha256_bytes(output_path.read_bytes())
    try:
        if result.returncode:
            raise ReviewHierarchyError(f"Codex exited with {result.returncode}")
        decision = load_object(output_path)
        contract_warnings = validate_outer_outer(decision, packet)
        public["contract_warnings"] = contract_warnings
        public["decision"] = decision
        public["status"] = "completed_valid"
    except Exception as error:
        public["failure"] = f"{type(error).__name__}: {error}"
    write_new_json(directory / "attempt-complete.json", public)
    append_event(
        event_log,
        "outer_adjudicator_attempt_completed",
        attempt_id=attempt_id,
        attempt_number=attempt_number,
        status=public["status"],
    )
    return public


def run_codex_outer_outer(
    run_id: str,
    packet: dict[str, Any],
    schema_path: Path,
    trace_root: Path,
    event_log: Path,
    model: str | None,
) -> dict[str, Any]:
    directory = trace_root / "outer-codex"
    directory.mkdir(parents=True, exist_ok=False)
    append_event(event_log, "outer_adjudicator_started", model=model or "codex_default")
    attempts: list[dict[str, Any]] = []
    repair: dict[str, Any] | None = None
    for attempt_number in range(1, MAX_CODEX_ATTEMPTS + 1):
        attempt_id = f"{run_id}-CODEX-A{attempt_number}"
        attempt = run_codex_outer_outer_attempt(
            packet,
            schema_path,
            directory / f"attempt-{attempt_number:02d}",
            event_log,
            model,
            attempt_id,
            attempt_number,
            repair,
        )
        attempts.append(attempt)
        if attempt["status"] == "completed_valid":
            break
        if attempt_number < MAX_CODEX_ATTEMPTS:
            repair = {
                "repair_of_attempt_id": attempt_id,
                "kind": "reissue_after_invalid_structured_adjudication",
                "diagnosis": attempt.get("failure", "invalid Codex adjudication"),
            }
            write_new_json(
                directory
                / f"repair-{attempt_number:02d}-to-{attempt_number + 1:02d}.json",
                repair,
            )
            append_event(
                event_log,
                "outer_adjudicator_repair_scheduled",
                failed_attempt_id=attempt_id,
                next_attempt_number=attempt_number + 1,
                repair_kind=repair["kind"],
            )
    terminal = attempts[-1]
    chain: dict[str, Any] = {
        "status": terminal["status"],
        "started_at_utc": attempts[0]["started_at_utc"],
        "completed_at_utc": terminal["completed_at_utc"],
        "elapsed_seconds": round(
            sum(float(attempt["elapsed_seconds"]) for attempt in attempts), 6
        ),
        "requested_model": model,
        "codex_cli_version": terminal["codex_cli_version"],
        "attempt_count": len(attempts),
        "repair_count": len(attempts) - 1,
        "invocation_count": len(attempts),
        "retry_allowed": False,
        "terminal_attempt_id": terminal["attempt_id"],
        "attempts": attempts,
    }
    for key in (
        "return_code",
        "contract_warnings",
        "decision",
        "failure",
        "last_message_byte_count",
        "last_message_sha256",
    ):
        if key in terminal:
            chain[key] = terminal[key]
    write_new_json(directory / "chain-complete.json", chain)
    append_event(
        event_log,
        "outer_adjudicator_completed",
        status=chain["status"],
        attempt_count=chain["attempt_count"],
        repair_count=chain["repair_count"],
    )
    return chain


def sanitized_summary(
    run_id: str,
    packet_bytes: bytes,
    teacher_chains: list[dict[str, Any]],
    codex_result: dict[str, Any],
    trace_root: Path,
) -> dict[str, Any]:
    teacher_attempts = [
        attempt for chain in teacher_chains for attempt in chain["attempts"]
    ]
    teacher_cost = sum(
        float((attempt.get("usage") or {}).get("cost") or 0)
        for attempt in teacher_attempts
    )
    return {
        "schema_version": PUBLIC_SCHEMA,
        "run_id": run_id,
        "completed_at_utc": now(),
        "architecture": {
            "primary_reviewer": "local Qwen",
            "independent_outer_teachers": ["GLM", "Kimi"],
            "teacher_execution": "parallel_fan_out_then_join",
            "invalid_invocation_policy": (
                "immutable linked repair attempts; never accepted as a teacher audit"
            ),
            "invalid_adjudication_policy": (
                "immutable linked Codex reissue; valid substantive decisions are "
                "never retried"
            ),
            "provider_transport": (
                "OpenRouter GLM plus first-party Moonshot Kimi; both streamed"
            ),
            "stream_deadlines_seconds": {
                "first_event": FIRST_EVENT_TIMEOUT_SECONDS,
                "idle": STREAM_IDLE_TIMEOUT_SECONDS,
                "total": TOTAL_RESPONSE_TIMEOUT_SECONDS,
            },
            "outer_adjudicator": "Codex",
            "fable_in_teacher_loop": False,
            "automatic_release_authority": False,
        },
        "qwen_packet": {
            "sha256": sha256_bytes(packet_bytes),
            "byte_count": len(packet_bytes),
        },
        "outer_teacher_chains": teacher_chains,
        "outer_teacher_attempts": teacher_attempts,
        "outer_teacher_valid_count": sum(
            chain["status"] == "completed_valid" for chain in teacher_chains
        ),
        "outer_teacher_total_reported_cost_usd": teacher_cost,
        "outer_adjudicator": codex_result,
        "trace_index": {
            **trace_evidence_index(trace_root),
            "raw_trace_public": False,
            "contents": (
                "Ignored local archive includes provider routes, system and user "
                "prompts, request bodies, raw SSE streams, parsed outputs, "
                "Codex JSONL events, stderr, version, and state records."
            ),
        },
        "release_control": {
            "publication_authorized": False,
            "training_signal_change_authorized": False,
            "author_email_dispatch_authorized": False,
            "separate_final_release_review_required": True,
        },
    }


def trace_evidence_index(trace_root: Path) -> dict[str, Any]:
    """Return the reproducible index for immutable evidence files.

    The local public-summary copy is excluded to avoid a circular hash. The
    summary is written only after the final event and run-complete record, so
    every indexed file is immutable when this function is called.
    """

    trace_files = sorted(
        path
        for path in trace_root.rglob("*")
        if path.is_file()
        and path.relative_to(trace_root) != Path("public-summary.json")
    )
    aggregate = b"".join(
        str(path.relative_to(trace_root)).encode()
        + b"\0"
        + sha256_bytes(path.read_bytes()).encode()
        + b"\n"
        for path in trace_files
    )
    return {
        "evidence_file_count": len(trace_files),
        "evidence_aggregate_sha256": sha256_bytes(aggregate),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--packet",
        type=Path,
        default=Path("extension/artifacts/outer_teacher_packet.json"),
    )
    parser.add_argument(
        "--teacher-schema",
        type=Path,
        default=Path("extension/outer_teacher_schema.json"),
    )
    parser.add_argument(
        "--outer-schema",
        type=Path,
        default=Path("extension/outer_outer_schema.json"),
    )
    parser.add_argument("--teacher-model", action="append", dest="teachers")
    parser.add_argument("--codex-model")
    parser.add_argument("--run-id")
    parser.add_argument("--trace-root", type=Path)
    parser.add_argument("--public-summary", type=Path)
    parser.add_argument(
        "--packet-only",
        action="store_true",
        help="Validate and archive the Qwen-only packet without invoking models.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}", run_id):
        raise SystemExit("REVIEW_HIERARCHY_FAILED: invalid run ID")
    trace_root = (
        args.trace_root or Path(".artifacts/review-hierarchy") / run_id
    ).resolve()
    if trace_root.exists():
        raise SystemExit("REVIEW_HIERARCHY_FAILED: trace root already exists")
    if args.public_summary and args.public_summary.exists():
        raise SystemExit("REVIEW_HIERARCHY_FAILED: public summary already exists")
    trace_root.mkdir(parents=True, exist_ok=False)
    event_log = trace_root / "events.jsonl"
    try:
        packet_bytes = args.packet.read_bytes()
        packet = json.loads(packet_bytes)
        if not isinstance(packet, dict):
            raise ReviewHierarchyError("Qwen packet is not an object")
        validate_qwen_packet(packet)
        teacher_schema = load_object(args.teacher_schema)
        load_object(args.outer_schema)
        teachers = tuple(args.teachers or DEFAULT_TEACHERS)
        if (
            len(teachers) != 2
            or len(set(teachers)) != 2
            or sum(model.startswith("z-ai/glm-") for model in teachers) != 1
            or sum(model.startswith("moonshotai/kimi-") for model in teachers) != 1
            or any(route_count(model) == 0 for model in teachers)
        ):
            raise ReviewHierarchyError(
                "teacher loop requires exactly one configured GLM and one "
                "configured Kimi model; Fable is prohibited"
            )
        write_new_bytes(trace_root / "qwen-packet.json", packet_bytes)
        write_new_bytes(
            trace_root / "outer-teacher-schema.json",
            args.teacher_schema.read_bytes(),
        )
        write_new_bytes(
            trace_root / "outer-schema.json", args.outer_schema.read_bytes()
        )
        write_new_json(
            trace_root / "run-start.json",
            {
                "schema_version": TRACE_SCHEMA,
                "run_id": run_id,
                "started_at_utc": now(),
                "architecture": ["Qwen", "GLM+Kimi", "Codex"],
                "teacher_execution": "parallel_fan_out_then_join",
                "invalid_invocation_policy": "immutable_linked_repair_attempts",
                "maximum_attempts_per_teacher": MAX_TEACHER_ATTEMPTS,
                "maximum_attempts_for_codex": MAX_CODEX_ATTEMPTS,
                "provider_transport": (
                    "OpenRouter GLM plus first-party Moonshot Kimi; both streamed"
                ),
                "stream_deadlines_seconds": {
                    "first_event": FIRST_EVENT_TIMEOUT_SECONDS,
                    "idle": STREAM_IDLE_TIMEOUT_SECONDS,
                    "total": TOTAL_RESPONSE_TIMEOUT_SECONDS,
                },
                "primary_provider_routes": {
                    model: route_for(model, 0).public_record() for model in teachers
                },
                "qwen_packet_sha256": sha256_bytes(packet_bytes),
                "teacher_schema_sha256": sha256_bytes(args.teacher_schema.read_bytes()),
                "outer_schema_sha256": sha256_bytes(args.outer_schema.read_bytes()),
                "fable_in_teacher_loop": False,
                "raw_trace_public": False,
                "automatic_release_authority": False,
            },
        )
        append_event(event_log, "run_started", run_id=run_id)
        if args.packet_only:
            append_event(event_log, "packet_only_complete", run_id=run_id)
            return 0

        key_names = {
            route_for(model, route_index).key_env
            for model in teachers
            for route_index in range(route_count(model))
        }
        provider_keys = {
            name: (
                os.environ.get(name, "")
                or (
                    os.environ.get("open_router", "")
                    if name == "OPENROUTER_API_KEY"
                    else ""
                )
            ).strip()
            for name in key_names
        }
        missing_primary = [
            route_for(model, 0).key_env
            for model in teachers
            if len(provider_keys[route_for(model, 0).key_env].strip("'\"")) < 8
        ]
        if missing_primary:
            raise ReviewHierarchyError(
                "missing primary teacher API keys: "
                + ", ".join(sorted(missing_primary))
            )
        chains = run_parallel_teachers(
            teachers,
            run_id,
            provider_keys,
            packet,
            teacher_schema,
            trace_root,
            event_log,
        )
        attempts = [attempt for chain in chains for attempt in chain["attempts"]]
        valid_teacher_count = sum(
            chain["status"] == "completed_valid" for chain in chains
        )
        if valid_teacher_count == 2:
            adjudication_packet = codex_packet(packet, attempts)
            write_new_json(trace_root / "outer-packet.json", adjudication_packet)
            codex_result = run_codex_outer_outer(
                run_id,
                adjudication_packet,
                args.outer_schema,
                trace_root,
                event_log,
                args.codex_model,
            )
        else:
            codex_result = {
                "status": "not_invoked",
                "reason": "one_or_more_teacher_repair_chains_exhausted",
                "invocation_count": 0,
                "retry_allowed": False,
            }
            append_event(
                event_log,
                "outer_adjudicator_blocked",
                valid_teacher_count=valid_teacher_count,
            )
        write_new_json(
            trace_root / "run-complete.json",
            {
                "schema_version": TRACE_SCHEMA,
                "run_id": run_id,
                "completed_at_utc": now(),
                "valid_outer_teacher_count": valid_teacher_count,
                "outer_adjudicator_status": codex_result["status"],
                "fable_in_teacher_loop": False,
            },
        )
        append_event(
            event_log,
            "run_completed",
            run_id=run_id,
            outer_teacher_valid_count=valid_teacher_count,
            outer_adjudicator_status=codex_result["status"],
        )
        summary = sanitized_summary(
            run_id, packet_bytes, chains, codex_result, trace_root
        )
        write_new_json(trace_root / "public-summary.json", summary)
        if args.public_summary:
            write_new_json(args.public_summary, summary)
        print(
            "REVIEW_HIERARCHY_COMPLETE "
            f"run_id={run_id} teachers={summary['outer_teacher_valid_count']}/2 "
            f"codex={codex_result['status']}"
        )
        return (
            0
            if summary["outer_teacher_valid_count"] == 2
            and codex_result["status"] == "completed_valid"
            else 4
        )
    except Exception as error:
        failure_detail = f"{type(error).__name__}: {error}"
        write_new_bytes(trace_root / "run-failure.txt", failure_detail.encode())
        failure = {
            "schema_version": TRACE_SCHEMA,
            "run_id": run_id,
            "failed_at_utc": now(),
            "failure": sanitize_failure_message(failure_detail),
            "failure_sha256": sha256_bytes(failure_detail.encode()),
        }
        write_new_json(trace_root / "run-failed.json", failure)
        append_event(event_log, "run_failed", failure=failure["failure"])
        print(f"REVIEW_HIERARCHY_FAILED: {failure['failure']}", file=os.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
