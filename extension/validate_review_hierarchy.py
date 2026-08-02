#!/usr/bin/env python3
"""Validate a completed NULSPEC review-hierarchy trace and bind its summary."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

if __package__:
    from .review_hierarchy import sha256_bytes, trace_evidence_index
else:
    from review_hierarchy import sha256_bytes, trace_evidence_index


VALIDATION_SCHEMA = "nulspec-review-hierarchy-validation-v1"


class TraceValidationError(RuntimeError):
    """Raised when a completed hierarchy cannot be reproduced from its trace."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise TraceValidationError(f"expected JSON object: {path.name}")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TraceValidationError(message)


def load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise TraceValidationError(
                f"invalid event JSON at line {line_number}"
            ) from error
        require(isinstance(value, dict), f"event {line_number} is not an object")
        events.append(value)
    require(bool(events), "event log is empty")
    return events


def validate_public_boundary(summary_path: Path) -> None:
    text = summary_path.read_text()
    forbidden_markers = (
        "/home/",
        "C:\\Users\\",
        "Authorization:",
        "Bearer ",
        "OPENROUTER_API_KEY",
        "MOONSHOT_API_KEY",
        "FIREWORKS_API_KEY",
    )
    found = [marker for marker in forbidden_markers if marker in text]
    require(not found, "public summary contains private marker(s): " + ", ".join(found))


def validate_completed_trace(
    trace_root: Path, summary_path: Path
) -> tuple[dict[str, Any], list[str]]:
    checks: list[str] = []
    required_global = (
        "qwen-packet.json",
        "outer-teacher-schema.json",
        "outer-schema.json",
        "run-start.json",
        "events.jsonl",
        "outer-packet.json",
        "run-complete.json",
        "public-summary.json",
    )
    for relative in required_global:
        require((trace_root / relative).is_file(), f"missing trace file: {relative}")
    checks.append("required_global_trace_files_present")

    summary = load_object(summary_path)
    schema_version = summary.get("schema_version")
    require(
        schema_version
        in {
            "nulspec-qwen-review-hierarchy-public-v2",
            "nulspec-qwen-review-hierarchy-public-v3",
        },
        "summary uses an unsupported schema version",
    )
    current_policy = schema_version == "nulspec-qwen-review-hierarchy-public-v3"
    local_summary_path = trace_root / "public-summary.json"
    require(
        local_summary_path.read_bytes() == summary_path.read_bytes(),
        "public summary differs from the trace-local copy",
    )
    validate_public_boundary(summary_path)
    checks.extend(("public_summary_copy_matches", "public_boundary_clean"))

    run_id = summary.get("run_id")
    require(isinstance(run_id, str) and bool(run_id), "summary has no run ID")
    run_start = load_object(trace_root / "run-start.json")
    run_complete = load_object(trace_root / "run-complete.json")
    require(run_start.get("run_id") == run_id, "run-start ID mismatch")
    require(run_complete.get("run_id") == run_id, "run-complete ID mismatch")
    require(
        run_start.get("fable_in_teacher_loop") is False, "Fable entered teacher loop"
    )
    require(
        run_complete.get("fable_in_teacher_loop") is False,
        "run-complete claims Fable entered teacher loop",
    )
    if current_policy:
        require(
            run_start.get("fable_active_review_allowed") is False,
            "run-start permits active per-paper Fable review",
        )
        require(
            run_complete.get("fable_active_review_allowed") is False,
            "run-complete permits active per-paper Fable review",
        )
    checks.append("run_identity_and_fable_boundary_valid")

    packet_bytes = (trace_root / "qwen-packet.json").read_bytes()
    packet_record = summary.get("qwen_packet") or {}
    require(
        packet_record.get("byte_count") == len(packet_bytes),
        "packet byte count mismatch",
    )
    require(
        packet_record.get("sha256") == sha256_bytes(packet_bytes),
        "packet hash mismatch",
    )
    checks.append("qwen_packet_hash_valid")

    architecture = summary.get("architecture") or {}
    require(
        architecture.get("teacher_execution") == "parallel_fan_out_then_join",
        "teacher execution is not parallel fan-out/join",
    )
    require(
        architecture.get("fable_in_teacher_loop") is False, "summary includes Fable"
    )
    if current_policy:
        require(
            architecture.get("fable_active_review_allowed") is False,
            "summary permits active per-paper Fable review",
        )
        require(
            architecture.get("fable_batch_cadence")
            == {
                "eligible_completed_papers": 10,
                "random_sample_size": 3,
                "invocations_per_batch": 1,
            },
            "summary has an invalid Fable batch cadence",
        )
    require(
        architecture.get("automatic_release_authority") is False,
        "summary grants automatic release authority",
    )
    release = summary.get("release_control") or {}
    for key in (
        "publication_authorized",
        "training_signal_change_authorized",
        "author_email_dispatch_authorized",
    ):
        require(
            release.get(key) is False, f"summary grants prohibited authority: {key}"
        )
    if current_policy:
        require(
            release.get("active_release_reviewers") == ["GLM", "Kimi"],
            "summary has invalid active release reviewers",
        )
        require(
            release.get("fable_batch_only") is True,
            "summary does not enforce batch-only Fable use",
        )
    checks.append("architecture_and_release_controls_valid")

    chains = summary.get("outer_teacher_chains")
    attempts = summary.get("outer_teacher_attempts")
    require(
        isinstance(chains, list) and len(chains) == 2, "expected two teacher chains"
    )
    require(
        isinstance(attempts, list) and len(attempts) >= 2, "teacher attempts missing"
    )
    require(
        {chain.get("reviewer_family") for chain in chains} == {"GLM", "Kimi"},
        "teacher families are not exactly GLM and Kimi",
    )
    require(
        all(chain.get("status") == "completed_valid" for chain in chains),
        "one or more teacher chains are invalid",
    )
    require(
        summary.get("outer_teacher_valid_count") == 2, "valid-teacher count mismatch"
    )

    attempt_files: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in trace_root.glob("outer-teachers/*/attempt-*/attempt-complete.json"):
        value = load_object(path)
        attempt_id = value.get("attempt_id")
        require(isinstance(attempt_id, str), f"attempt has no ID: {path}")
        require(attempt_id not in attempt_files, f"duplicate attempt ID: {attempt_id}")
        attempt_files[attempt_id] = (path.parent, value)
    require(len(attempt_files) == len(attempts), "attempt file count mismatch")

    invoked_attempt_files = (
        "attempt-start.json",
        "request.json",
        "system-prompt.txt",
        "user-prompt.txt",
    )
    bound_trace_files = {
        "request": "request.json",
        "response_headers": "response-headers.json",
        "raw_response": "raw-response.sse",
        "stream_events": "stream-events.jsonl",
        "assembled_response": "assembled-response.json",
        "parsed_audit": "parsed-audit.json",
    }
    for public_attempt in attempts:
        attempt_id = public_attempt.get("attempt_id")
        require(attempt_id in attempt_files, f"attempt trace missing: {attempt_id}")
        directory, traced_attempt = attempt_files[attempt_id]
        require(
            traced_attempt == public_attempt, f"attempt summary mismatch: {attempt_id}"
        )
        require(
            (directory / "attempt-complete.json").is_file(),
            f"missing attempt-complete.json for {attempt_id}",
        )
        if public_attempt.get("model_invocation_count"):
            for name in invoked_attempt_files:
                require(
                    (directory / name).is_file(), f"missing {name} for {attempt_id}"
                )
        if public_attempt.get("status") == "completed_valid":
            for field_prefix, name in bound_trace_files.items():
                path = directory / name
                require(
                    path.is_file() and path.stat().st_size > 0,
                    f"missing {name} for {attempt_id}",
                )
                raw = path.read_bytes()
                require(
                    public_attempt.get(f"{field_prefix}_byte_count") == len(raw),
                    f"{name} byte count mismatch for {attempt_id}",
                )
                require(
                    public_attempt.get(f"{field_prefix}_sha256") == sha256_bytes(raw),
                    f"{name} hash mismatch for {attempt_id}",
                )
        else:
            require(
                (directory / "failure.txt").is_file(),
                f"failure not retained for {attempt_id}",
            )
    checks.append("teacher_attempt_files_and_summaries_valid")

    chain_files: dict[str, dict[str, Any]] = {}
    for path in trace_root.glob("outer-teachers/*/chain-complete.json"):
        value = load_object(path)
        family = value.get("reviewer_family")
        require(isinstance(family, str), f"chain has no family: {path}")
        chain_files[family] = value
    require(set(chain_files) == {"GLM", "Kimi"}, "chain trace files missing")
    for chain in chains:
        require(
            chain_files[chain["reviewer_family"]] == chain,
            f"chain summary mismatch: {chain['reviewer_family']}",
        )
    checks.append("teacher_chain_files_match")

    codex = summary.get("outer_adjudicator") or {}
    require(codex.get("status") == "completed_valid", "Codex adjudication is invalid")
    codex_directory = trace_root / "outer-codex"
    codex_attempts = codex.get("attempts")
    require(
        isinstance(codex_attempts, list) and bool(codex_attempts),
        "Codex attempt chain is missing",
    )
    require(
        load_object(codex_directory / "chain-complete.json") == codex,
        "Codex chain summary mismatch",
    )
    require(
        codex.get("attempt_count") == len(codex_attempts),
        "Codex attempt count mismatch",
    )
    require(
        codex.get("repair_count") == len(codex_attempts) - 1,
        "Codex repair count mismatch",
    )
    for index, codex_attempt in enumerate(codex_attempts, start=1):
        attempt_directory = codex_directory / f"attempt-{index:02d}"
        for name in (
            "attempt-start.json",
            "attempt-complete.json",
            "codex-version.txt",
            "prompt.txt",
            "stdout.jsonl",
            "stderr.txt",
        ):
            require(
                (attempt_directory / name).is_file(),
                f"missing Codex trace file: attempt-{index:02d}/{name}",
            )
        last_message = attempt_directory / "last-message.json"
        if codex_attempt.get("last_message_byte_count") is not None:
            require(last_message.is_file(), f"Codex last message missing: {index}")
            raw_last_message = last_message.read_bytes()
            require(
                codex_attempt.get("last_message_byte_count") == len(raw_last_message),
                f"Codex last-message byte count mismatch: {index}",
            )
            require(
                codex_attempt.get("last_message_sha256")
                == sha256_bytes(raw_last_message),
                f"Codex last-message hash mismatch: {index}",
            )
        elif codex_attempt.get("status") == "completed_valid":
            raise TraceValidationError(f"valid Codex attempt {index} has no output")
        require(
            load_object(attempt_directory / "attempt-complete.json") == codex_attempt,
            f"Codex attempt summary mismatch: {index}",
        )
        if codex_attempt.get("status") != "completed_valid":
            require(
                isinstance(codex_attempt.get("failure"), str),
                f"invalid Codex attempt {index} has no failure",
            )
            require(
                index < len(codex_attempts),
                "terminal Codex attempt is invalid",
            )
            require(
                (
                    codex_directory / f"repair-{index:02d}-to-{index + 1:02d}.json"
                ).is_file(),
                f"Codex repair link missing after attempt {index}",
            )
    require(
        codex.get("terminal_attempt_id") == codex_attempts[-1].get("attempt_id"),
        "Codex terminal attempt ID mismatch",
    )
    checks.append("codex_trace_and_summary_valid")

    events = load_events(trace_root / "events.jsonl")
    event_names = [event.get("event") for event in events]
    teacher_starts = [
        index
        for index, name in enumerate(event_names)
        if name == "outer_teacher_started"
    ]
    teacher_completions = [
        index
        for index, name in enumerate(event_names)
        if name == "outer_teacher_completed"
    ]
    chain_completions = [
        index
        for index, name in enumerate(event_names)
        if name == "outer_teacher_chain_completed"
    ]
    require(len(teacher_starts) >= 2, "teacher start events missing")
    require(len(teacher_completions) >= 2, "teacher completion events missing")
    require(
        max(teacher_starts[:2]) < min(teacher_completions),
        "teachers did not fan out before completion",
    )
    require(len(chain_completions) == 2, "teacher chain completion events missing")
    require("outer_adjudicator_started" in event_names, "Codex start event missing")
    codex_start = event_names.index("outer_adjudicator_started")
    require(
        max(chain_completions) < codex_start,
        "Codex started before both teacher chains joined",
    )
    require(event_names[-1] == "run_completed", "run_completed is not the final event")
    require(events[-1].get("run_id") == run_id, "final event run ID mismatch")
    checks.append("event_order_and_parallel_join_valid")

    expected_index = summary.get("trace_index") or {}
    observed_index = trace_evidence_index(trace_root)
    for key, value in observed_index.items():
        require(expected_index.get(key) == value, f"trace index mismatch: {key}")
    checks.append("aggregate_trace_hash_reproducible")
    return summary, checks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-root", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise SystemExit("TRACE_VALIDATION_FAILED: output already exists")
    try:
        summary, checks = validate_completed_trace(args.trace_root, args.summary)
        summary_bytes = args.summary.read_bytes()
        record = {
            "schema_version": VALIDATION_SCHEMA,
            "pipeline_run_id": summary["run_id"],
            "validated_at_utc": now(),
            "status": "passed",
            "checks": checks,
            "trace_index": trace_evidence_index(args.trace_root),
            "public_summary": {
                "byte_count": len(summary_bytes),
                "sha256": sha256_bytes(summary_bytes),
            },
            "commands": [
                {
                    "command": "validate_completed_trace",
                    "exit_code": 0,
                    "check_count": len(checks),
                },
                {
                    "command": "recompute_trace_evidence_index",
                    "exit_code": 0,
                    **trace_evidence_index(args.trace_root),
                },
            ],
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        print(f"REVIEW_HIERARCHY_VALID run_id={summary['run_id']} checks={len(checks)}")
        return 0
    except Exception as error:
        print(f"TRACE_VALIDATION_FAILED: {type(error).__name__}: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
