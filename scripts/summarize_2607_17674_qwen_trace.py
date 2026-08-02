#!/usr/bin/env python3
"""Create append-only usage and timing accounting for a local Qwen trace."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class AccountingError(RuntimeError):
    """Raised when a trace cannot support exact local-run accounting."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise AccountingError("event timestamp is missing or non-string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise AccountingError(f"invalid event timestamp: {value}") from error
    if parsed.tzinfo is None:
        raise AccountingError("event timestamp lacks a timezone")
    return parsed.astimezone(timezone.utc)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AccountingError(f"could not read valid JSON: {path.name}") from error
    if not isinstance(value, dict):
        raise AccountingError(f"expected a JSON object: {path.name}")
    return value


def load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as error:
                    raise AccountingError(
                        f"events line {line_number} is invalid JSON"
                    ) from error
                if not isinstance(event, dict):
                    raise AccountingError(f"events line {line_number} is not an object")
                events.append(event)
    except OSError as error:
        raise AccountingError("could not read events.jsonl") from error
    if not events:
        raise AccountingError("events.jsonl is empty")
    return events


def local_route_labels(run_input: dict[str, Any]) -> list[str]:
    routes = run_input.get("routes")
    if not isinstance(routes, list) or not routes:
        raise AccountingError("run input contains no routes")
    labels: list[str] = []
    for route in routes:
        if not isinstance(route, dict):
            raise AccountingError("route metadata is malformed")
        label = route.get("label")
        base_url = route.get("base_url")
        if not isinstance(label, str) or not isinstance(base_url, str):
            raise AccountingError("route label or URL is malformed")
        parsed = urlparse(base_url)
        if parsed.scheme != "http" or parsed.hostname not in {
            "127.0.0.1",
            "localhost",
            "::1",
        }:
            raise AccountingError("provider-charge zero requires loopback-only routes")
        labels.append(label)
    if len(set(labels)) != len(labels):
        raise AccountingError("route labels are not unique")
    return sorted(labels)


def verify_trace_index(trace_root: Path, trace_index: dict[str, Any]) -> dict[str, Any]:
    """Require every current trace byte to match the supplied sealed index."""

    content_index = trace_index.get("content_index")
    records = trace_index.get("files")
    if not isinstance(content_index, dict) or not isinstance(records, list):
        raise AccountingError("trace index lacks content metadata or file records")
    if (
        content_index.get("algorithm")
        != "sha256-utf8-relative-path-tab-bytes-tab-file-sha256-newline-v1"
    ):
        raise AccountingError("trace index uses an unsupported algorithm")

    current_paths = sorted(
        trace_root.rglob("*"),
        key=lambda path: path.relative_to(trace_root).as_posix().encode("utf-8"),
    )
    current_files: list[Path] = []
    for path in current_paths:
        relative_path = path.relative_to(trace_root).as_posix()
        if path.is_symlink():
            raise AccountingError(f"trace contains a symlink: {relative_path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise AccountingError(f"trace contains a non-regular file: {relative_path}")
        current_files.append(path)
    if len(current_files) != len(records):
        raise AccountingError("current trace file count differs from sealed index")

    record_stream = hashlib.sha256()
    total_bytes = 0
    seen: set[str] = set()
    for path, record in zip(current_files, records, strict=True):
        if not isinstance(record, dict):
            raise AccountingError("trace index file record is malformed")
        relative_path = path.relative_to(trace_root).as_posix()
        if relative_path in seen:
            raise AccountingError("trace index contains a duplicate path")
        seen.add(relative_path)
        if record.get("relative_path") != relative_path:
            raise AccountingError("current trace path order differs from sealed index")
        before = path.stat()
        digest = sha256_file(path)
        after = path.stat()
        if (
            before.st_ino != after.st_ino
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
        ):
            raise AccountingError("trace file changed while its index was verified")
        if record.get("bytes") != after.st_size or record.get("sha256") != digest:
            raise AccountingError(
                f"current trace file differs from index: {relative_path}"
            )
        total_bytes += after.st_size
        record_stream.update(
            f"{relative_path}\t{after.st_size}\t{digest}\n".encode("utf-8")
        )
    expected = {
        "algorithm": "sha256-utf8-relative-path-tab-bytes-tab-file-sha256-newline-v1",
        "file_count": len(current_files),
        "total_bytes": total_bytes,
        "records_sha256": record_stream.hexdigest(),
    }
    if content_index != expected:
        raise AccountingError("trace content summary differs from sealed index")
    return content_index


def require_path_outside_trace(trace_root: Path, candidate: Path) -> None:
    try:
        candidate.expanduser().resolve().relative_to(trace_root.expanduser().resolve())
    except ValueError:
        return
    raise AccountingError("accounting output must be outside the trace root")


def phase_intervals(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    starts: dict[str, datetime] = {}
    intervals: list[dict[str, Any]] = []
    for event in events:
        event_name = event.get("event")
        phase = event.get("phase")
        if event_name == "qwen_phase_started":
            if not isinstance(phase, str) or phase in starts:
                raise AccountingError("phase start is missing or duplicated")
            starts[phase] = parse_utc(event.get("at_utc"))
        elif event_name == "qwen_phase_resumed":
            if not isinstance(phase, str) or phase not in starts:
                raise AccountingError("phase resume lacks an unmatched start")
        elif event_name in {"qwen_phase_completed", "qwen_phase_failed"}:
            if not isinstance(phase, str) or phase not in starts:
                raise AccountingError("phase terminal event lacks a unique start")
            started = starts.pop(phase)
            completed = parse_utc(event.get("at_utc"))
            elapsed = (completed - started).total_seconds()
            if elapsed < 0:
                raise AccountingError("phase terminal timestamp precedes its start")
            intervals.append(
                {
                    "phase": phase,
                    "terminal_event": event_name,
                    "started_at_utc": started.isoformat().replace("+00:00", "Z"),
                    "completed_at_utc": completed.isoformat().replace("+00:00", "Z"),
                    "elapsed_seconds": elapsed,
                }
            )
    if starts:
        raise AccountingError("trace contains a nonterminal phase")
    if not intervals:
        raise AccountingError("trace contains no terminal phase")
    return intervals


def attempt_accounting(trace_root: Path) -> dict[str, Any]:
    paths = sorted(trace_root.glob("sources/**/attempt-record.json"))
    if not paths:
        raise AccountingError("trace contains no attempt records")

    prompt_tokens = 0
    completion_tokens = 0
    request_elapsed = 0.0
    valid_count = 0
    response_count = 0
    no_response_count = 0
    transport_elapsed_count = 0
    timestamp_elapsed_count = 0
    bindings: list[dict[str, Any]] = []
    for path in paths:
        record = load_object(path)
        valid = record.get("valid")
        if not isinstance(valid, bool):
            raise AccountingError("attempt validity is missing or non-boolean")
        valid_count += int(valid)
        transport = record.get("transport")
        if transport is None:
            started = parse_utc(record.get("started_at_utc"))
            completed = parse_utc(record.get("completed_at_utc"))
            elapsed = (completed - started).total_seconds()
            if elapsed < 0:
                raise AccountingError("attempt terminal timestamp precedes its start")
            usage = None
            no_response_count += 1
            timestamp_elapsed_count += 1
        elif isinstance(transport, dict):
            elapsed = transport.get("elapsed_seconds")
            if (
                not isinstance(elapsed, (int, float))
                or isinstance(elapsed, bool)
                or not math.isfinite(float(elapsed))
                or elapsed < 0
            ):
                raise AccountingError("attempt elapsed time is invalid")
            usage = transport.get("usage")
            transport_elapsed_count += 1
        else:
            raise AccountingError("attempt transport record is malformed")
        request_elapsed += float(elapsed)
        if usage is not None:
            if not isinstance(usage, dict):
                raise AccountingError("attempt usage record is malformed")
            prompt = usage.get("prompt_tokens")
            completion = usage.get("completion_tokens")
            if (
                not isinstance(prompt, int)
                or isinstance(prompt, bool)
                or prompt < 0
                or not isinstance(completion, int)
                or isinstance(completion, bool)
                or completion < 0
            ):
                raise AccountingError("attempt token usage is invalid")
            prompt_tokens += prompt
            completion_tokens += completion
            response_count += 1
        elif transport is not None:
            no_response_count += 1
        bindings.append(
            {
                "relative_path": path.relative_to(trace_root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "valid": valid,
            }
        )
    return {
        "attempt_count": len(paths),
        "valid_attempt_count": valid_count,
        "invalid_attempt_count": len(paths) - valid_count,
        "completed_response_count": response_count,
        "no_response_attempt_count": no_response_count,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "accelerator_request_wall_clock_seconds": request_elapsed,
        "transport_elapsed_attempt_count": transport_elapsed_count,
        "timestamp_elapsed_attempt_count": timestamp_elapsed_count,
        "attempt_record_bindings": bindings,
    }


def summarize(
    trace_root: Path,
    trace_index_path: Path,
    scope_label: str,
    *,
    created_at_utc: str | None = None,
) -> dict[str, Any]:
    """Build exact local-provider usage and timing accounting."""

    trace_root = trace_root.expanduser()
    if trace_root.is_symlink():
        raise AccountingError("trace root must not be a symlink")
    trace_root = trace_root.resolve()
    trace_index_path = trace_index_path.expanduser().resolve()
    if not trace_root.is_dir():
        raise AccountingError("trace root must be an existing directory")
    if not scope_label or any(character.isspace() for character in scope_label):
        raise AccountingError("scope label must be a nonempty token")

    run_input_path = trace_root / "run-input.json"
    events_path = trace_root / "events.jsonl"
    run_input = load_object(run_input_path)
    if run_input.get("paper_id") != "2607.17674":
        raise AccountingError("trace is not bound to paper 2607.17674")
    route_labels = local_route_labels(run_input)
    events = load_events(events_path)
    intervals = phase_intervals(events)
    attempts = attempt_accounting(trace_root)
    trace_index = load_object(trace_index_path)
    if trace_index.get("root_basename") != trace_root.name:
        raise AccountingError("trace index is bound to a different root")
    content_index = verify_trace_index(trace_root, trace_index)

    final_reviews = sorted(trace_root.glob("sources/*/final-review.json"))
    terminal_events = [interval["terminal_event"] for interval in intervals]
    phase_wall_clock = sum(interval["elapsed_seconds"] for interval in intervals)
    phase_resume_count = sum(
        event.get("event") == "qwen_phase_resumed" for event in events
    )
    return {
        "schema_version": 1,
        "paper_id": "2607.17674",
        "created_at_utc": created_at_utc or utc_now(),
        "scope_label": scope_label,
        "trace": {
            "root_basename": trace_root.name,
            "run_input": {
                "bytes": run_input_path.stat().st_size,
                "sha256": sha256_file(run_input_path),
            },
            "events": {
                "bytes": events_path.stat().st_size,
                "sha256": sha256_file(events_path),
            },
            "content_index": {
                "index_basename": trace_index_path.name,
                "index_sha256": sha256_file(trace_index_path),
                **content_index,
            },
            "final_review_count": len(final_reviews),
            "phase_intervals": intervals,
            "terminal_state": (
                "completed"
                if all(event == "qwen_phase_completed" for event in terminal_events)
                else "failed"
            ),
        },
        "runtime": {
            "runtime_protocol_version": run_input.get("runtime_protocol_version"),
            "route_class": "local_self_hosted_qwen",
            "route_labels": route_labels,
            "gguf": run_input.get("gguf"),
            "llama_server": run_input.get("llama_server"),
        },
        "usage": {
            key: attempts[key]
            for key in (
                "attempt_count",
                "valid_attempt_count",
                "invalid_attempt_count",
                "completed_response_count",
                "no_response_attempt_count",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
            )
        },
        "timing": {
            "accelerator_request_wall_clock_seconds": attempts[
                "accelerator_request_wall_clock_seconds"
            ],
            "transport_elapsed_attempt_count": attempts[
                "transport_elapsed_attempt_count"
            ],
            "timestamp_elapsed_attempt_count": attempts[
                "timestamp_elapsed_attempt_count"
            ],
            "experimental_phase_wall_clock_seconds": phase_wall_clock,
            "phase_resume_event_count": phase_resume_count,
            "definition": (
                "Request time sums every retained local model attempt; phase time "
                "spans each first start through terminal event and therefore includes "
                "offline time inside a resumed phase."
                if phase_resume_count
                else "Request time sums every retained local model attempt; phase time "
                "sums each traced phase interval and excludes gaps between phases."
            ),
        },
        "cost": {
            "currency": "USD",
            "provider_charge_usd": 0,
            "provider_charge_status": "exact_loopback_self_hosted_route",
            "electricity_cost_usd": None,
            "electricity_cost_status": "not_measured_no_power_meter",
            "hardware_capital_cost_usd": None,
            "hardware_capital_cost_status": "not_allocated",
        },
        "attempt_record_bindings": attempts["attempt_record_bindings"],
        "controls": {
            "estimated_cost_presented_as_exact": False,
            "teacher_input_authorized": False,
            "publication_authorized": False,
            "training_authorized": False,
            "email_authorized": False,
        },
    }


def write_new(path: Path, value: dict[str, Any]) -> None:
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path = path.expanduser().resolve()
    if not path.parent.is_dir():
        raise AccountingError("output parent must be an existing directory")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as error:
        raise AccountingError("refusing to overwrite existing accounting") from error
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-root", type=Path, required=True)
    parser.add_argument("--trace-index", type=Path, required=True)
    parser.add_argument("--scope-label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        require_path_outside_trace(args.trace_root, args.output)
        result = summarize(args.trace_root, args.trace_index, args.scope_label)
        write_new(args.output, result)
    except AccountingError as error:
        raise SystemExit(str(error)) from error
    print(
        json.dumps(
            {
                "output_basename": args.output.name,
                "output_sha256": sha256_file(args.output),
                "scope_label": result["scope_label"],
                "terminal_state": result["trace"]["terminal_state"],
                "usage": result["usage"],
                "timing": result["timing"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
