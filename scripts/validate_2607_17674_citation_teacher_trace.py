#!/usr/bin/env python3
"""Validate the complete GLM/Kimi/Codex citation-teacher trace."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[1]
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from extension.direct_teacher_providers import PROVIDER_ROUTES
from scripts.citation_teacher_contract import (
    validate_codex_record,
    validate_teacher_record,
)
from scripts.run_2607_17674_codex_citation_adjudication import (
    build_codex_packet,
)

PROTOCOL_ROOT = WORKSPACE / "protocols" / "2607.17674"
STUDY_WORK_ROOT = WORKSPACE / "research" / "replications" / "2607.17674" / "work"
DEFAULT_CONFIG = PROTOCOL_ROOT / "citation_teacher_config.v1.0.3.json"
TEACHER_SCHEMA = PROTOCOL_ROOT / "citation_teacher_audit.schema.json"
CODEX_SCHEMA = PROTOCOL_ROOT / "citation_codex_adjudication.schema.json"


def verify_harness_bindings(config: dict[str, Any]) -> None:
    paths = {
        "teacher_contract_sha256": WORKSPACE / "scripts" / "citation_teacher_contract.py",
        "teacher_runner_sha256": WORKSPACE
        / "scripts"
        / "run_2607_17674_citation_teachers.py",
        "codex_runner_sha256": WORKSPACE
        / "scripts"
        / "run_2607_17674_codex_citation_adjudication.py",
        "trace_validator_sha256": Path(__file__).resolve(),
        "packet_builder_sha256": WORKSPACE
        / "scripts"
        / "build_2607_17674_citation_teacher_packet.py",
    }
    for key, path in paths.items():
        if sha256_file(path) != config["bindings"][key]:
            raise TraceValidationError(f"frozen harness binding differs: {key}")


class TraceValidationError(RuntimeError):
    """Raised when an append-only hierarchy trace fails closed."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TraceValidationError(f"expected JSON object: {path}")
    return value


def write_new_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write((json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def validate_artifact_bindings(root: Path, record: dict[str, Any]) -> None:
    listed = record.get("artifacts")
    if not isinstance(listed, list):
        raise TraceValidationError(f"artifact list missing: {root}")
    expected: dict[str, Path] = {
        path.name: path
        for path in root.iterdir()
        if path.is_file() and path.name != "attempt-record.json"
    }
    observed: set[str] = set()
    for binding in listed:
        if not isinstance(binding, dict) or not isinstance(
            binding.get("relative_path"), str
        ):
            raise TraceValidationError(f"malformed artifact binding: {root}")
        name = binding["relative_path"]
        if name in observed or name not in expected:
            raise TraceValidationError(f"duplicate or absent bound artifact: {root / name}")
        observed.add(name)
        path = expected[name]
        if binding.get("bytes") != path.stat().st_size:
            raise TraceValidationError(f"artifact byte count differs: {path}")
        if binding.get("sha256") != sha256_file(path):
            raise TraceValidationError(f"artifact hash differs: {path}")
    if observed != set(expected):
        raise TraceValidationError(f"unbound attempt artifacts: {root}")


def sequential_attempts(root: Path) -> list[Path]:
    attempts = sorted(path for path in root.glob("attempt-*") if path.is_dir())
    expected = [f"attempt-{index:02d}" for index in range(1, len(attempts) + 1)]
    if [path.name for path in attempts] != expected:
        raise TraceValidationError(f"attempt numbering is not contiguous: {root}")
    return attempts


def accepted_record(root: Path) -> tuple[dict[str, Any], dict[str, Any], Path]:
    accepted = load_object(root / "accepted.json")
    parsed_path = root / str(accepted["parsed_relative_path"])
    if sha256_file(parsed_path) != accepted["parsed_sha256"]:
        raise TraceValidationError(f"accepted parsed hash differs: {root}")
    return accepted, load_object(parsed_path), parsed_path


def validate_teacher_chain(
    root: Path,
    teacher: str,
    requested_model: str,
    packet: dict[str, Any],
    packet_sha256: str,
    schema: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    attempts = sequential_attempts(root)
    if not attempts:
        raise TraceValidationError(f"teacher has no attempts: {teacher}")
    allowed_routes = {
        (route.route_id, route.provider_name, route.provider_model_id)
        for route in PROVIDER_ROUTES[requested_model]
    }
    valid_attempts: list[Path] = []
    accounted = 0.0
    unknown_cost = False
    for attempt in attempts:
        record = load_object(attempt / "attempt-record.json")
        validate_artifact_bindings(attempt, record)
        if record.get("logical_teacher") != teacher:
            raise TraceValidationError(f"teacher identity differs: {attempt}")
        if record.get("requested_model") != requested_model:
            raise TraceValidationError(f"requested model differs: {attempt}")
        if record.get("packet_sha256") != packet_sha256:
            raise TraceValidationError(f"teacher packet hash differs: {attempt}")
        route = record.get("route", {})
        route_identity = (
            route.get("route_id"),
            route.get("provider_name"),
            route.get("provider_model_id"),
        )
        if route_identity not in allowed_routes:
            raise TraceValidationError(f"unregistered provider route: {attempt}")
        accounting = record.get("accounting", {})
        value = accounting.get("accounted_cost_usd")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            raise TraceValidationError(f"invalid provider accounting: {attempt}")
        accounted += float(value)
        unknown_cost = unknown_cost or (
            accounting.get("accounting_basis")
            == "conservative_upper_bound_due_to_missing_usage"
        )
        if record.get("valid") is True:
            valid_attempts.append(attempt)
            parsed = load_object(attempt / "parsed.json")
            errors = validate_teacher_record(parsed, packet, schema)
            if errors:
                raise TraceValidationError(f"schema-valid teacher attempt failed: {errors}")
        elif not record.get("errors"):
            raise TraceValidationError(f"invalid teacher attempt has no errors: {attempt}")
        transport = record.get("transport")
        raw_path = attempt / "raw-response.sse"
        if (
            isinstance(transport, dict)
            and raw_path.is_file()
            and transport.get("raw_response_sha256") != sha256_file(raw_path)
        ):
            raise TraceValidationError(f"raw provider stream hash differs: {attempt}")
    if len(valid_attempts) != 1 or valid_attempts[0] != attempts[-1]:
        raise TraceValidationError(
            f"{teacher} must have one terminal valid substantive attempt"
        )
    accepted, parsed, parsed_path = accepted_record(root)
    if parsed_path.parent != valid_attempts[0]:
        raise TraceValidationError(f"accepted {teacher} attempt is not terminal valid attempt")
    if accepted.get("logical_teacher") != teacher:
        raise TraceValidationError(f"accepted teacher identity differs: {teacher}")
    return parsed, {
        "attempts": len(attempts),
        "invalid_attempts": len(attempts) - 1,
        "accounted_cost_usd": round(accounted, 12),
        "unknown_cost": unknown_cost,
    }


def validate_codex_chain(
    root: Path,
    packet: dict[str, Any],
    teacher_records: dict[str, dict[str, Any]],
    schema: dict[str, Any],
    config: dict[str, Any],
    packet_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    attempts = sequential_attempts(root)
    if not attempts:
        raise TraceValidationError("Codex has no attempts")
    valid_attempts: list[Path] = []
    for attempt in attempts:
        record = load_object(attempt / "attempt-record.json")
        validate_artifact_bindings(attempt, record)
        if record.get("packet_sha256") != packet_sha256:
            raise TraceValidationError(f"Codex packet hash differs: {attempt}")
        if record.get("requested_model") != config["codex_execution"]["requested_model"]:
            raise TraceValidationError(f"Codex requested model differs: {attempt}")
        if record.get("reasoning_effort") != config["codex_execution"]["reasoning_effort"]:
            raise TraceValidationError(f"Codex reasoning effort differs: {attempt}")
        billing = record.get("billing", {})
        if billing.get("basis") != "Codex subscription" or billing.get(
            "metered_cost_usd"
        ) is not None:
            raise TraceValidationError(f"Codex subscription accounting differs: {attempt}")
        event_path = attempt / "events.jsonl"
        if event_path.is_file():
            for number, line in enumerate(event_path.read_text().splitlines(), start=1):
                if line.strip():
                    try:
                        json.loads(line)
                    except json.JSONDecodeError as error:
                        raise TraceValidationError(
                            f"Codex event {number} is not JSON: {attempt}"
                        ) from error
        if record.get("valid") is True:
            valid_attempts.append(attempt)
            parsed = load_object(attempt / "parsed.json")
            errors = validate_codex_record(parsed, packet, teacher_records, schema)
            if errors:
                raise TraceValidationError(f"valid Codex record failed checks: {errors}")
        elif not record.get("errors"):
            raise TraceValidationError(f"invalid Codex attempt has no errors: {attempt}")
    if len(valid_attempts) != 1 or valid_attempts[0] != attempts[-1]:
        raise TraceValidationError("Codex must have one terminal valid substantive attempt")
    _, parsed, parsed_path = accepted_record(root)
    if parsed_path.parent != valid_attempts[0]:
        raise TraceValidationError("accepted Codex attempt is not terminal valid attempt")
    return parsed, {"attempts": len(attempts), "invalid_attempts": len(attempts) - 1}


def validate_trace(
    packet_path: Path, trace_root: Path, config_path: Path
) -> dict[str, Any]:
    packet = load_object(packet_path)
    packet_sha256 = sha256_file(packet_path)
    config = load_object(config_path)
    verify_harness_bindings(config)
    teacher_schema = load_object(TEACHER_SCHEMA)
    codex_schema = load_object(CODEX_SCHEMA)
    run_input = load_object(trace_root / "run-input.json")
    if run_input.get("teacher_packet", {}).get("sha256") != packet_sha256:
        raise TraceValidationError("run input points to a different teacher packet")
    if run_input.get("config_sha256") != sha256_file(config_path):
        raise TraceValidationError("run input points to a different teacher config")
    models = {item["logical_id"]: item["requested_model"] for item in config["teachers"]}
    teacher_records: dict[str, dict[str, Any]] = {}
    teacher_summaries: dict[str, dict[str, Any]] = {}
    for teacher in ("glm", "kimi"):
        record, summary = validate_teacher_chain(
            trace_root / "teachers" / teacher,
            teacher,
            models[teacher],
            packet,
            packet_sha256,
            teacher_schema,
        )
        teacher_records[teacher] = record
        teacher_summaries[teacher] = summary
    completion = load_object(trace_root / "teacher-completion.json")
    if completion.get("teacher_packet_sha256") != packet_sha256:
        raise TraceValidationError("teacher completion packet hash differs")
    completion_spend = completion.get("spend", {}).get("spent_usd", {})
    for teacher in ("glm", "kimi"):
        if abs(
            float(completion_spend.get(teacher, -1))
            - teacher_summaries[teacher]["accounted_cost_usd"]
        ) > 1e-9:
            raise TraceValidationError(f"teacher completion spend differs: {teacher}")

    expected_codex_packet, _ = build_codex_packet(
        packet, packet_sha256, trace_root, teacher_schema
    )
    codex_packet_path = trace_root / "codex-packet.json"
    if load_object(codex_packet_path) != expected_codex_packet:
        raise TraceValidationError("Codex packet cannot be deterministically reconstructed")
    codex_packet_sha256 = sha256_file(codex_packet_path)
    codex_record, codex_summary = validate_codex_chain(
        trace_root / "codex",
        expected_codex_packet["qwen_packet"],
        teacher_records,
        codex_schema,
        config,
        codex_packet_sha256,
    )
    codex_completion = load_object(trace_root / "codex-completion.json")
    if codex_completion.get("codex_packet_sha256") != codex_packet_sha256:
        raise TraceValidationError("Codex completion packet hash differs")
    if codex_completion.get("overall_assessment") != codex_record["overall_assessment"]:
        raise TraceValidationError("Codex completion assessment differs")
    if codex_completion.get("final_qwen_reviewer_quality_score") != codex_record[
        "final_qwen_reviewer_quality_score"
    ]:
        raise TraceValidationError("Codex completion score differs")
    return {
        "schema_version": 1,
        "paper_id": "2607.17674",
        "validated_at_utc": utc_now(),
        "valid": True,
        "teacher_packet_sha256": packet_sha256,
        "teacher_completion_sha256": sha256_file(
            trace_root / "teacher-completion.json"
        ),
        "codex_packet_sha256": codex_packet_sha256,
        "codex_completion_sha256": sha256_file(trace_root / "codex-completion.json"),
        "teacher_summaries": teacher_summaries,
        "codex_summary": codex_summary,
        "final_qwen_reviewer_quality_score": codex_record[
            "final_qwen_reviewer_quality_score"
        ],
        "overall_assessment": codex_record["overall_assessment"],
        "release_authority": False,
        "email_authority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--teacher-packet", type=Path, required=True)
    parser.add_argument("--teacher-trace-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    packet_path = args.teacher_packet.expanduser().resolve()
    trace_root = args.teacher_trace_root.expanduser().resolve()
    output = args.output.expanduser().resolve()
    try:
        trace_root.relative_to(STUDY_WORK_ROOT.resolve())
        output.relative_to(STUDY_WORK_ROOT.resolve())
    except ValueError as error:
        raise SystemExit(f"trace and output must be inside {STUDY_WORK_ROOT}") from error
    report = validate_trace(packet_path, trace_root, args.config.expanduser().resolve())
    write_new_json(output, report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
