#!/usr/bin/env python3
"""Exercise both Qwen citation grammars against the exact live llama runtime."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from run_2607_17674_qwen_citation_audit import (
    DEFAULT_EVIDENCE_SCHEMA,
    DEFAULT_REVIEW_SCHEMA,
    PROTOCOL_ROOT,
    STUDY_WORK_ROOT,
    AuditError,
    acquire_experiment_lock,
    build_request,
    effective_evidence_repair_prompt,
    experiment_lock_path,
    load_object,
    route_metadata,
    sha256_file,
    stream_completion,
    utc_now,
    write_new_json,
    write_new_text,
)

DEFAULT_CONFIG = PROTOCOL_ROOT / "citation_audit_config.v1.0.6.json"
GRAMMAR_FAILURE_MARKERS = (
    "error parsing grammar",
    "failed to parse grammar",
    "exceeds sane defaults",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--route", default="http://127.0.0.1:8080")
    parser.add_argument("--server-log", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()

    output_root = args.output_root.expanduser().resolve()
    config_path = args.config.expanduser().resolve()
    server_log = args.server_log.expanduser().resolve()
    try:
        output_root.relative_to(STUDY_WORK_ROOT.resolve())
    except ValueError as error:
        raise SystemExit("output root must be inside the study work tree") from error
    if output_root.exists():
        raise SystemExit("refusing to overwrite runtime preflight output")
    if not server_log.is_file():
        raise SystemExit("server log is missing")
    config = load_object(config_path)
    if config.get("protocol_version") not in {
        "1.0.2",
        "1.0.3",
        "1.0.4",
        "1.0.5",
        "1.0.6",
    }:
        raise SystemExit("runtime preflight requires config v1.0.2 through v1.0.6")

    try:
        evidence_repair_prompt, evidence_repair_prompt_binding = (
            effective_evidence_repair_prompt(config)
        )
    except AuditError as error:
        raise SystemExit(str(error)) from error

    try:
        experiment_lock = acquire_experiment_lock()
    except AuditError as error:
        raise SystemExit(str(error)) from error
    output_root.mkdir(parents=True)
    write_new_json(
        output_root / "preflight-input.json",
        {
            "schema_version": 1,
            "paper_id": "2607.17674",
            "config_sha256": sha256_file(config_path),
            "evidence_repair_prompt": evidence_repair_prompt_binding,
            "experiment_lock": {
                "basename": experiment_lock_path().name,
                "mechanism": "flock-exclusive-nonblocking",
                "held": not experiment_lock.closed,
            },
        },
    )
    log_start = server_log.stat().st_size
    route = route_metadata("runtime-preflight", args.route)
    write_new_json(output_root / "route.json", route)
    cases = [
        (
            "evidence",
            DEFAULT_EVIDENCE_SCHEMA,
            config["primary_reviewer"]["evidence_generation"],
            None,
            None,
        ),
        (
            "synthesis",
            DEFAULT_REVIEW_SCHEMA,
            config["primary_reviewer"]["synthesis_generation"],
            None,
            None,
        ),
    ]
    if evidence_repair_prompt is not None:
        cases.insert(
            1,
            (
                "evidence-repair",
                DEFAULT_EVIDENCE_SCHEMA,
                config["primary_reviewer"]["evidence_generation"],
                [
                    (
                        "evidence_candidates[0].excerpt is not grounded in one "
                        "physical source line on the cited page"
                    )
                ],
                evidence_repair_prompt,
            ),
        )
    case_records: list[dict[str, object]] = []
    for name, schema_path, registered_generation, repair_errors, repair_prompt in cases:
        case_root = output_root / name
        case_root.mkdir()
        schema = load_object(schema_path)
        generation = dict(registered_generation)
        generation["maximum_output_tokens"] = 1
        request, user_prompt = build_request(
            str(route["model_alias"]),
            "This is a decoding-grammar preflight. Return the required JSON object.",
            {"runtime_preflight": True, "schema_case": name},
            schema,
            generation,
            config["primary_reviewer"]["chat_template_kwargs"],
            repair_errors,
            repair_prompt,
        )
        write_new_json(case_root / "canonical-schema.json", schema)
        write_new_json(
            case_root / "transport-schema.json",
            request["response_format"]["json_schema"]["schema"],
        )
        write_new_text(case_root / "user-prompt.txt", user_prompt)
        write_new_json(case_root / "request.json", request)
        response = stream_completion(
            str(route["base_url"]),
            request,
            case_root / "raw-response.sse",
            case_root / "normalized-events.jsonl",
            30,
            30,
            120,
        )
        write_new_json(case_root / "assembled-response.json", response)
        case_records.append(
            {
                "name": name,
                "canonical_schema_sha256": sha256_file(
                    case_root / "canonical-schema.json"
                ),
                "transport_schema_sha256": sha256_file(
                    case_root / "transport-schema.json"
                ),
                "request_sha256": sha256_file(case_root / "request.json"),
                "response_sha256": sha256_file(case_root / "assembled-response.json"),
                "http_status": response["http_status"],
                "event_count": response["event_count"],
            }
        )

    time.sleep(0.25)
    with server_log.open("rb") as handle:
        handle.seek(log_start)
        log_slice = handle.read().decode("utf-8", errors="replace")
    write_new_text(output_root / "server-log-slice.txt", log_slice)
    lowered_log = log_slice.lower()
    failures = [marker for marker in GRAMMAR_FAILURE_MARKERS if marker in lowered_log]
    completion = {
        "schema_version": 1,
        "paper_id": "2607.17674",
        "preflight_type": "exact_llama_runtime_transport_grammar",
        "completed_at_utc": utc_now(),
        "config_sha256": sha256_file(config_path),
        "experiment_lock": {
            "basename": experiment_lock_path().name,
            "mechanism": "flock-exclusive-nonblocking",
            "held": not experiment_lock.closed,
        },
        "server_log_snapshot_sha256": sha256_file(server_log),
        "server_log_snapshot_bytes": server_log.stat().st_size,
        "server_log_start_bytes": log_start,
        "server_log_slice_sha256": sha256_file(output_root / "server-log-slice.txt"),
        "cases": case_records,
        "grammar_failure_markers": failures,
        "passed": not failures
        and all(case["http_status"] == 200 for case in case_records),
    }
    write_new_json(output_root / "preflight-completion.json", completion)
    print(json.dumps(completion, indent=2, sort_keys=True))
    if not completion["passed"]:
        raise SystemExit("exact llama runtime grammar preflight failed")


if __name__ == "__main__":
    main()
