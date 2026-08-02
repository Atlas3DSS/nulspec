import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "scripts" / "summarize_2607_17674_qwen_trace.py"
SPEC = importlib.util.spec_from_file_location("summarize_2607_17674_qwen_trace", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def build_trace(tmp_path: Path) -> tuple[Path, Path]:
    trace = tmp_path / "attempt-01"
    write_json(
        trace / "run-input.json",
        {
            "paper_id": "2607.17674",
            "runtime_protocol_version": "1.0.4",
            "routes": [
                {
                    "label": "workstation",
                    "base_url": "http://127.0.0.1:8080",
                }
            ],
            "gguf": {"sha256": "model"},
            "llama_server": {"sha256": "server"},
        },
    )
    events = [
        {
            "at_utc": "2026-08-02T00:00:00Z",
            "event": "qwen_audit_started",
        },
        {
            "at_utc": "2026-08-02T00:00:01Z",
            "event": "qwen_phase_started",
            "phase": "calibration",
        },
        {
            "at_utc": "2026-08-02T00:00:11Z",
            "event": "qwen_phase_completed",
            "phase": "calibration",
        },
    ]
    (trace / "events.jsonl").write_text(
        "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8"
    )
    write_json(
        trace / "sources" / "sourceA" / "evidence" / "chunk-1" / "attempt-record.json",
        {
            "valid": True,
            "transport": {
                "elapsed_seconds": 4.25,
                "usage": {"prompt_tokens": 10, "completion_tokens": 3},
            },
        },
    )
    write_json(
        trace / "sources" / "sourceA" / "synthesis" / "attempt-record.json",
        {
            "valid": False,
            "transport": {
                "elapsed_seconds": 5.5,
                "usage": {"prompt_tokens": 12, "completion_tokens": 4},
            },
        },
    )
    write_json(
        trace / "sources" / "sourceB" / "evidence" / "chunk-1" / "attempt-record.json",
        {
            "started_at_utc": "2026-08-02T00:00:03Z",
            "completed_at_utc": "2026-08-02T00:00:05Z",
            "valid": False,
            "transport": None,
        },
    )
    write_json(trace / "sources" / "sourceA" / "final-review.json", {})
    trace_index = tmp_path / "trace-index.json"
    records = []
    record_stream = hashlib.sha256()
    total_bytes = 0
    for path in sorted(
        (candidate for candidate in trace.rglob("*") if candidate.is_file()),
        key=lambda candidate: candidate.relative_to(trace).as_posix().encode("utf-8"),
    ):
        relative_path = path.relative_to(trace).as_posix()
        size = path.stat().st_size
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        records.append(
            {"relative_path": relative_path, "bytes": size, "sha256": digest}
        )
        record_stream.update(f"{relative_path}\t{size}\t{digest}\n".encode())
        total_bytes += size
    write_json(
        trace_index,
        {
            "root_basename": trace.name,
            "content_index": {
                "algorithm": "sha256-utf8-relative-path-tab-bytes-tab-file-sha256-newline-v1",
                "file_count": len(records),
                "total_bytes": total_bytes,
                "records_sha256": record_stream.hexdigest(),
            },
            "files": records,
        },
    )
    return trace, trace_index


def test_summarize_reports_exact_local_usage_and_excludes_phase_gaps(
    tmp_path: Path,
) -> None:
    trace, trace_index = build_trace(tmp_path)

    result = MODULE.summarize(
        trace,
        trace_index,
        "calibration",
        created_at_utc="2026-08-02T01:00:00Z",
    )

    assert result["usage"] == {
        "attempt_count": 3,
        "valid_attempt_count": 1,
        "invalid_attempt_count": 2,
        "completed_response_count": 2,
        "no_response_attempt_count": 1,
        "prompt_tokens": 22,
        "completion_tokens": 7,
        "total_tokens": 29,
    }
    assert result["timing"]["accelerator_request_wall_clock_seconds"] == 11.75
    assert result["timing"]["transport_elapsed_attempt_count"] == 2
    assert result["timing"]["timestamp_elapsed_attempt_count"] == 1
    assert result["timing"]["experimental_phase_wall_clock_seconds"] == 10
    assert result["cost"]["provider_charge_usd"] == 0
    assert result["trace"]["final_review_count"] == 1
    assert result["trace"]["terminal_state"] == "completed"
    assert result["controls"]["teacher_input_authorized"] is False


def test_summarize_rejects_nonloopback_route(tmp_path: Path) -> None:
    trace, trace_index = build_trace(tmp_path)
    run_input = json.loads((trace / "run-input.json").read_text(encoding="utf-8"))
    run_input["routes"][0]["base_url"] = "https://provider.example/v1"
    write_json(trace / "run-input.json", run_input)

    with pytest.raises(MODULE.AccountingError, match="loopback-only"):
        MODULE.summarize(trace, trace_index, "calibration")


def test_summarize_rejects_nonterminal_phase(tmp_path: Path) -> None:
    trace, trace_index = build_trace(tmp_path)
    with (trace / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "at_utc": "2026-08-02T00:00:12Z",
                    "event": "qwen_phase_started",
                    "phase": "remaining",
                }
            )
            + "\n"
        )

    with pytest.raises(MODULE.AccountingError, match="nonterminal phase"):
        MODULE.summarize(trace, trace_index, "full")


def test_phase_intervals_accept_registered_resume_event() -> None:
    intervals = MODULE.phase_intervals(
        [
            {
                "at_utc": "2026-08-02T00:00:00Z",
                "event": "qwen_phase_started",
                "phase": "remaining",
            },
            {
                "at_utc": "2026-08-02T00:01:00Z",
                "event": "qwen_phase_resumed",
                "phase": "remaining",
            },
            {
                "at_utc": "2026-08-02T00:02:00Z",
                "event": "qwen_phase_completed",
                "phase": "remaining",
            },
        ]
    )
    assert intervals[0]["elapsed_seconds"] == 120


def test_phase_intervals_reject_resume_without_start() -> None:
    with pytest.raises(MODULE.AccountingError, match="resume lacks"):
        MODULE.phase_intervals(
            [
                {
                    "at_utc": "2026-08-02T00:01:00Z",
                    "event": "qwen_phase_resumed",
                    "phase": "remaining",
                }
            ]
        )


def test_summarize_rejects_trace_changed_after_index(tmp_path: Path) -> None:
    trace, trace_index = build_trace(tmp_path)
    write_json(trace / "sources" / "sourceA" / "final-review.json", {"changed": True})

    with pytest.raises(MODULE.AccountingError, match="differs from index"):
        MODULE.summarize(trace, trace_index, "calibration")


def test_summarize_rejects_output_inside_trace(tmp_path: Path) -> None:
    trace, _ = build_trace(tmp_path)

    with pytest.raises(MODULE.AccountingError, match="outside"):
        MODULE.require_path_outside_trace(trace, trace / "accounting.json")


def test_write_new_refuses_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "accounting.json"
    MODULE.write_new(output, {"first": True})

    with pytest.raises(MODULE.AccountingError, match="refusing to overwrite"):
        MODULE.write_new(output, {"second": True})
