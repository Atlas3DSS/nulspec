#!/usr/bin/env python3
"""Request one batched advisory Fable critique for validated paper pipelines."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import tempfile
import time
from typing import Any


TRACE_SCHEMA = "nulspec-fable-pipeline-critique-trace-v1"
PUBLIC_SCHEMA = "nulspec-fable-pipeline-critique-public-v1"
BATCH_SCHEMA = "nulspec-fable-pipeline-critique-batch-input-v1"
SCOPE = "pipeline_architecture_and_trace_only"
FABLE_BATCH_SIZE = 10
FABLE_SAMPLE_SIZE = FABLE_BATCH_SIZE // 3
MAX_BATCH_PACKET_BYTES = 850_000
DEFAULT_SOURCE_PATHS = (
    Path("docs/REVIEW_HIERARCHY.md"),
    Path("extension/review_hierarchy.py"),
    Path("extension/direct_teacher_providers.py"),
    Path("extension/validate_review_hierarchy.py"),
    Path("extension/outer_teacher_schema.json"),
    Path("extension/outer_outer_schema.json"),
    Path("extension/fable_pipeline_critique_schema.json"),
    Path("extension/README.md"),
    Path("extension/EXPLAINER.md"),
)


class CritiqueError(RuntimeError):
    """Raised when a critique precondition or response contract fails."""


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
    record = {"at_utc": now(), "event": event, **fields}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        handle.write(json.dumps(record, sort_keys=True).encode() + b"\n")


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise CritiqueError(f"expected a JSON object: {path}")
    return value


def validate_pipeline_summary(summary: dict[str, Any]) -> None:
    architecture = summary.get("architecture") or {}
    if architecture.get("teacher_execution") != "parallel_fan_out_then_join":
        raise CritiqueError("pipeline summary is not a parallel teacher run")
    if architecture.get("fable_in_teacher_loop") is not False:
        raise CritiqueError("pipeline summary includes Fable in the teacher loop")
    chains = summary.get("outer_teacher_chains")
    if not isinstance(chains, list) or len(chains) != 2:
        raise CritiqueError("pipeline summary does not contain two teacher chains")
    families = {chain.get("reviewer_family") for chain in chains}
    if families != {"GLM", "Kimi"} or any(
        chain.get("status") != "completed_valid" for chain in chains
    ):
        raise CritiqueError("both GLM and Kimi chains must end with valid audits")
    if summary.get("outer_teacher_valid_count") != 2:
        raise CritiqueError("pipeline summary valid-teacher count is not two")
    outer = summary.get("outer_adjudicator") or {}
    if outer.get("status") != "completed_valid":
        raise CritiqueError("Codex adjudication is not valid")
    controls = summary.get("release_control") or {}
    if any(
        controls.get(key) is not False
        for key in (
            "publication_authorized",
            "training_signal_change_authorized",
            "author_email_dispatch_authorized",
        )
    ):
        raise CritiqueError("pipeline summary grants prohibited authority")
    if controls.get("fable_batch_only") is False:
        raise CritiqueError("pipeline summary permits active per-paper Fable review")
    active_reviewers = controls.get("active_release_reviewers")
    if active_reviewers is not None and active_reviewers != ["GLM", "Kimi"]:
        raise CritiqueError("pipeline summary has invalid active release reviewers")


def validate_validation_record(
    record: dict[str, Any], summary: dict[str, Any] | None = None
) -> None:
    if record.get("status") != "passed":
        raise CritiqueError("pipeline validation record has not passed")
    commands = record.get("commands")
    if not isinstance(commands, list) or not commands:
        raise CritiqueError("pipeline validation record has no commands")
    if any(
        not isinstance(command, dict) or command.get("exit_code") != 0
        for command in commands
    ):
        raise CritiqueError("pipeline validation record contains a failed command")
    if summary is not None:
        if record.get("pipeline_run_id") != summary.get("run_id"):
            raise CritiqueError("pipeline validation record is for a different run")
        validated_index = record.get("trace_index") or {}
        summary_index = summary.get("trace_index") or {}
        for key in ("evidence_file_count", "evidence_aggregate_sha256"):
            if validated_index.get(key) != summary_index.get(key):
                raise CritiqueError(f"pipeline validation record has a different {key}")


def source_record(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "byte_count": len(raw),
        "sha256": sha256_bytes(raw),
        "content": raw.decode(),
    }


def validate_relative_input_path(value: Any, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise CritiqueError(f"{field} must be a nonempty repository-relative path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise CritiqueError(f"{field} must stay inside the repository")
    return path


def load_batch_manifest(
    manifest_path: Path, repository_root: Path
) -> tuple[str, list[dict[str, Any]]]:
    """Load exactly ten complete, repository-bound paper pipeline records."""

    manifest = load_object(manifest_path)
    if manifest.get("schema_version") != BATCH_SCHEMA:
        raise CritiqueError("batch manifest has an unsupported schema version")
    batch_id = manifest.get("batch_id")
    if not isinstance(batch_id, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}", batch_id
    ):
        raise CritiqueError("batch manifest has an invalid batch ID")
    records = manifest.get("papers")
    if not isinstance(records, list) or len(records) != FABLE_BATCH_SIZE:
        raise CritiqueError(
            f"batch manifest must contain exactly {FABLE_BATCH_SIZE} papers"
        )

    papers: list[dict[str, Any]] = []
    study_ids: set[str] = set()
    allowed = {"study_id", "pipeline_summary", "validation", "corrections"}
    for index, record in enumerate(records):
        if not isinstance(record, dict) or set(record) != allowed:
            raise CritiqueError(f"batch paper {index} has invalid fields")
        study_id = record.get("study_id")
        if not isinstance(study_id, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}", study_id
        ):
            raise CritiqueError(f"batch paper {index} has an invalid study ID")
        if study_id in study_ids:
            raise CritiqueError(f"batch contains duplicate study ID {study_id}")
        study_ids.add(study_id)

        paths = {}
        for field in ("pipeline_summary", "validation", "corrections"):
            candidate = (
                repository_root / validate_relative_input_path(record[field], field)
            ).resolve()
            if not candidate.is_relative_to(repository_root):
                raise CritiqueError(f"{field} resolves outside the repository")
            paths[field] = candidate
        summary = load_object(paths["pipeline_summary"])
        validation = load_object(paths["validation"])
        corrections = load_object(paths["corrections"])
        validate_pipeline_summary(summary)
        validate_validation_record(validation, summary)
        papers.append(
            {
                "study_id": study_id,
                "source_paths": {
                    field: paths[field].relative_to(repository_root).as_posix()
                    for field in paths
                },
                "completed_pipeline_summary": summary,
                "validation_record": validation,
                "architecture_corrections": corrections,
            }
        )
    return batch_id, papers


def select_batch_samples(
    papers: list[dict[str, Any]], selection_seed: str
) -> list[dict[str, Any]]:
    """Select three of ten papers reproducibly, independent of manifest order."""

    if len(papers) != FABLE_BATCH_SIZE:
        raise CritiqueError(
            f"selection requires exactly {FABLE_BATCH_SIZE} validated papers"
        )
    if not re.fullmatch(r"[0-9a-f]{64}", selection_seed):
        raise CritiqueError("selection seed must be 32 bytes encoded as lowercase hex")
    ordered = sorted(papers, key=lambda paper: paper["study_id"])
    seed_bytes = bytes.fromhex(selection_seed)
    ranked = sorted(
        ordered,
        key=lambda paper: (
            hashlib.sha256(
                seed_bytes + b"\0" + str(paper["study_id"]).encode()
            ).digest(),
            str(paper["study_id"]),
        ),
    )
    return ranked[:FABLE_SAMPLE_SIZE]


def build_batch_packet(
    batch_id: str,
    all_papers: list[dict[str, Any]],
    selected_papers: list[dict[str, Any]],
    selection_seed: str,
) -> dict[str, Any]:
    all_ids = sorted(str(paper["study_id"]) for paper in all_papers)
    selected_ids = sorted(str(paper["study_id"]) for paper in selected_papers)
    if len(all_ids) != FABLE_BATCH_SIZE or len(set(all_ids)) != FABLE_BATCH_SIZE:
        raise CritiqueError("batch packet requires ten unique papers")
    if len(selected_ids) != FABLE_SAMPLE_SIZE or not set(selected_ids) <= set(all_ids):
        raise CritiqueError(
            "batch packet requires three members of the ten-paper batch"
        )
    return {
        "protocol": {
            "name": "nulspec-batched-fable-pipeline-critique-v1",
            "scope": SCOPE,
            "role": (
                "Advisory critique of sampled completed review pipelines. Fable "
                "is not a teacher, release reviewer, scientific vote, or authority."
            ),
            "evidence_boundary": (
                "Repository-native pipeline code, schemas, documentation, and "
                "three sanitized completed-run records from one ten-paper batch."
            ),
            "cadence": {
                "eligible_completed_papers": FABLE_BATCH_SIZE,
                "random_sample_size": FABLE_SAMPLE_SIZE,
                "invocations_per_batch": 1,
                "selection_method": "sha256_seeded_rank_v1",
                "selection_seed_hex": selection_seed,
                "all_study_ids": all_ids,
                "selected_study_ids": selected_ids,
            },
            "invocation_limit": 1,
            "automatic_retry": False,
            "automatic_changes_authorized": False,
        },
        "batch_id": batch_id,
        "sources": {
            path.as_posix(): source_record(path) for path in DEFAULT_SOURCE_PATHS
        },
        "pipeline_samples": selected_papers,
    }


def claim_batch(
    registry_path: Path,
    *,
    batch_id: str,
    run_id: str,
    all_study_ids: list[str],
    selected_study_ids: list[str],
    selection_seed: str,
    packet_sha256: str,
) -> dict[str, Any]:
    """Append one locked claim and reject reuse of a batch or any constituent paper."""

    if len(all_study_ids) != FABLE_BATCH_SIZE or len(set(all_study_ids)) != len(
        all_study_ids
    ):
        raise CritiqueError("batch registry claim requires ten unique study IDs")
    if (
        len(selected_study_ids) != FABLE_SAMPLE_SIZE
        or len(set(selected_study_ids)) != len(selected_study_ids)
        or not set(selected_study_ids) <= set(all_study_ids)
    ):
        raise CritiqueError("batch registry claim requires three selected study IDs")
    if not re.fullmatch(r"[0-9a-f]{64}", selection_seed):
        raise CritiqueError("batch registry claim has an invalid selection seed")
    if not re.fullmatch(r"[0-9a-f]{64}", packet_sha256):
        raise CritiqueError("batch registry claim has an invalid packet hash")
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    claim = {
        "schema_version": "nulspec-fable-batch-registry-v1",
        "claimed_at_utc": now(),
        "batch_id": batch_id,
        "run_id": run_id,
        "all_study_ids": sorted(all_study_ids),
        "selected_study_ids": sorted(selected_study_ids),
        "selection_seed_hex": selection_seed,
        "packet_sha256": packet_sha256,
        "automatic_retry_allowed": False,
    }
    with registry_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        used_batch_ids: set[str] = set()
        used_study_ids: set[str] = set()
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                existing = json.loads(line)
            except json.JSONDecodeError as error:
                raise CritiqueError(
                    f"batch registry line {line_number} is invalid JSON"
                ) from error
            if not isinstance(existing, dict):
                raise CritiqueError(
                    f"batch registry line {line_number} is not an object"
                )
            used_batch_ids.add(str(existing.get("batch_id")))
            existing_ids = existing.get("all_study_ids")
            if not isinstance(existing_ids, list) or not all(
                isinstance(study_id, str) for study_id in existing_ids
            ):
                raise CritiqueError(
                    f"batch registry line {line_number} has invalid study IDs"
                )
            used_study_ids.update(existing_ids)
        if batch_id in used_batch_ids:
            raise CritiqueError(f"batch ID {batch_id} was already claimed")
        reused = sorted(set(all_study_ids) & used_study_ids)
        if reused:
            raise CritiqueError(
                "papers were already used in a Fable batch: " + ", ".join(reused)
            )
        handle.seek(0, os.SEEK_END)
        handle.write(json.dumps(claim, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return claim


def critique_prompt(packet: dict[str, Any]) -> str:
    return (
        "Critique the sampled completed NULSPEC Qwen/GLM/Kimi/Codex review "
        "pipelines as one batch. Compare the three samples where useful. Assess "
        "architecture, independence, evidence boundaries, concurrent "
        "fan-out and join behavior, invalid-invocation repair policy, failure "
        "taxonomy, trace integrity, cost controls, release-authority controls, "
        "documentation, and validation coverage. Be factual and charitable. "
        "Identify NULSPEC's own implementation mistakes as directly as external "
        "failures. Do not inspect or infer unseen study content. Do not cast a "
        "teacher vote, scientific verdict, or release vote. Do not recommend "
        "changing frozen Qwen results from this critique. Cite exact packet "
        "paths for every strength and finding. Return exactly the structured "
        "object required by the schema, with scope_confirmation set to "
        f"{SCOPE}.\n\nPIPELINE CRITIQUE PACKET:\n"
        + json.dumps(packet, indent=2, sort_keys=True)
    )


def result_event(wrapper: Any) -> dict[str, Any]:
    if isinstance(wrapper, dict):
        return wrapper
    if isinstance(wrapper, list):
        results = [
            event
            for event in wrapper
            if isinstance(event, dict) and event.get("type") == "result"
        ]
        if results:
            return results[-1]
    raise CritiqueError("Claude wrapper contains no result event")


def validate_critique(value: dict[str, Any]) -> None:
    if value.get("scope_confirmation") != SCOPE:
        raise CritiqueError("Fable critique failed the scope gate")
    if value.get("overall_assessment") not in {
        "sound",
        "sound_with_changes",
        "material_changes_required",
        "not_auditable",
    }:
        raise CritiqueError("Fable critique has an invalid assessment")
    confidence = value.get("confidence")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise CritiqueError("Fable critique has invalid confidence")
    authority = value.get("authority_confirmation")
    if authority != {
        "is_teacher_vote": False,
        "can_change_qwen_results": False,
        "can_change_training_signals": False,
        "can_authorize_publication": False,
        "can_authorize_email": False,
    }:
        raise CritiqueError("Fable critique returned invalid authority controls")
    if not isinstance(value.get("findings"), list):
        raise CritiqueError("Fable critique findings are not an array")


def validate_claude_cli_schema(schema: dict[str, Any]) -> None:
    """Reject schema declarations the installed Claude CLI cannot resolve."""

    if "$schema" in schema:
        raise CritiqueError(
            "Claude CLI structured-output schema must omit the $schema declaration"
        )

    def check_refs(value: Any) -> None:
        if isinstance(value, dict):
            reference = value.get("$ref")
            if isinstance(reference, str) and not reference.startswith("#/"):
                raise CritiqueError("Claude CLI schema contains an external $ref")
            for child in value.values():
                check_refs(child)
        elif isinstance(value, list):
            for child in value:
                check_refs(child)

    check_refs(schema)


def public_model_usage(event: dict[str, Any]) -> dict[str, Any]:
    usage = event.get("modelUsage")
    if not isinstance(usage, dict):
        return {}
    allowed = (
        "inputTokens",
        "outputTokens",
        "cacheReadInputTokens",
        "cacheCreationInputTokens",
        "costUSD",
        "contextWindow",
        "maxOutputTokens",
    )
    return {
        str(model): {key: row[key] for key in allowed if key in row}
        for model, row in usage.items()
        if isinstance(row, dict)
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--batch-manifest",
        type=Path,
        required=True,
        help="required manifest containing exactly ten validated paper pipelines",
    )
    parser.add_argument(
        "--batch-registry",
        type=Path,
        default=Path(".artifacts/fable-pipeline-critique/batch-registry.jsonl"),
    )
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path("."),
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("extension/fable_pipeline_critique_schema.json"),
    )
    parser.add_argument(
        "--run-id",
        required=True,
    )
    parser.add_argument(
        "--trace-root",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--public-result",
        type=Path,
        required=True,
    )
    parser.add_argument("--max-budget-usd", type=float, default=5.0)
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}", args.run_id):
        raise SystemExit("FABLE_PIPELINE_CRITIQUE_FAILED: invalid run ID")
    if args.trace_root.exists():
        raise SystemExit("FABLE_PIPELINE_CRITIQUE_FAILED: trace root exists")
    if args.public_result.exists():
        raise SystemExit("FABLE_PIPELINE_CRITIQUE_FAILED: public result exists")
    if not 0 < args.max_budget_usd <= 5:
        raise SystemExit("FABLE_PIPELINE_CRITIQUE_FAILED: budget must not exceed $5")

    try:
        schema = load_object(args.schema)
        validate_claude_cli_schema(schema)
        repository_root = args.repository_root.resolve()
        batch_id, papers = load_batch_manifest(args.batch_manifest, repository_root)
        selection_seed = secrets.token_hex(32)
        selected = select_batch_samples(papers, selection_seed)
        packet = build_batch_packet(batch_id, papers, selected, selection_seed)
        batch_metadata = {
            "batch_id": batch_id,
            "eligible_completed_paper_count": FABLE_BATCH_SIZE,
            "sampled_paper_count": FABLE_SAMPLE_SIZE,
            "all_study_ids": sorted(paper["study_id"] for paper in papers),
            "selected_study_ids": sorted(paper["study_id"] for paper in selected),
            "selection_seed_hex": selection_seed,
        }
        role = "batched_advisory_pipeline_critique"
        packet_bytes = encoded_json(packet)
        if len(packet_bytes) > MAX_BATCH_PACKET_BYTES:
            raise CritiqueError(
                f"critique packet is {len(packet_bytes)} bytes; maximum is "
                f"{MAX_BATCH_PACKET_BYTES}"
            )
        prompt = critique_prompt(packet)
    except (CritiqueError, OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"FABLE_PIPELINE_CRITIQUE_FAILED: {error}") from error

    args.trace_root.mkdir(parents=True, exist_ok=False)
    event_log = args.trace_root / "events.jsonl"
    write_new_bytes(args.trace_root / "packet.json", packet_bytes)
    write_new_bytes(args.trace_root / "schema.json", args.schema.read_bytes())
    write_new_bytes(args.trace_root / "prompt.txt", prompt.encode())
    version = subprocess.run(
        ["claude", "--version"], text=True, capture_output=True, check=False
    )
    write_new_bytes(args.trace_root / "claude-version.txt", version.stdout.encode())
    try:
        claim_batch(
            args.batch_registry,
            batch_id=batch_metadata["batch_id"],
            run_id=args.run_id,
            all_study_ids=batch_metadata["all_study_ids"],
            selected_study_ids=batch_metadata["selected_study_ids"],
            selection_seed=batch_metadata["selection_seed_hex"],
            packet_sha256=sha256_bytes(packet_bytes),
        )
    except (CritiqueError, OSError) as error:
        write_new_bytes(
            args.trace_root / "pre-model-failure.txt",
            f"{type(error).__name__}: {error}".encode(),
        )
        raise SystemExit(f"FABLE_PIPELINE_CRITIQUE_FAILED: {error}") from error
    started_at = now()
    write_new_json(
        args.trace_root / "attempt-start.json",
        {
            "schema_version": TRACE_SCHEMA,
            "run_id": args.run_id,
            "started_at_utc": started_at,
            "role": role,
            "model_alias": "fable",
            "effort": "max",
            "tools_allowed": [],
            "session_persistence": False,
            "invocation_count": 1,
            "retry_allowed": False,
            **batch_metadata,
            "max_budget_usd": args.max_budget_usd,
            "packet_byte_count": len(packet_bytes),
            "packet_sha256": sha256_bytes(packet_bytes),
            "prompt_sha256": sha256_bytes(prompt.encode()),
            "schema_sha256": sha256_bytes(args.schema.read_bytes()),
            "claude_cli_version": version.stdout.strip(),
        },
    )
    append_event(event_log, "fable_pipeline_critique_started", run_id=args.run_id)

    command = [
        "claude",
        "--print",
        "--model",
        "fable",
        "--effort",
        "max",
        "--tools",
        "",
        "--disable-slash-commands",
        "--no-session-persistence",
        "--safe-mode",
        "--permission-mode",
        "dontAsk",
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(schema, separators=(",", ":")),
        "--max-budget-usd",
        str(args.max_budget_usd),
    ]
    environment = os.environ.copy()
    for name in (
        "ANTHROPIC_API_KEY",
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
        "CODEX_API_KEY",
    ):
        environment.pop(name, None)
    with tempfile.TemporaryDirectory(prefix="nulspec-fable-critique-") as isolated:
        start = time.monotonic()
        result = subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            check=False,
            cwd=isolated,
            env=environment,
        )
        elapsed = round(time.monotonic() - start, 6)

    stdout = result.stdout.encode()
    stderr = result.stderr.encode()
    write_new_bytes(args.trace_root / "raw-stdout.json", stdout)
    write_new_bytes(args.trace_root / "stderr.txt", stderr)
    completed_at = now()
    public: dict[str, Any] = {
        "schema_version": PUBLIC_SCHEMA,
        "run_id": args.run_id,
        "role": role,
        "status": "completed_invalid",
        "started_at_utc": started_at,
        "completed_at_utc": completed_at,
        "elapsed_seconds": elapsed,
        "model_alias": "fable",
        "effort": "max",
        "invocation_count": 1,
        "retry_allowed": False,
        **batch_metadata,
        "decision_weight": 0,
        "is_teacher_vote": False,
        "automatic_changes_authorized": False,
        "return_code": result.returncode,
        "packet_byte_count": len(packet_bytes),
        "packet_sha256": sha256_bytes(packet_bytes),
        "prompt_sha256": sha256_bytes(prompt.encode()),
        "raw_stdout_byte_count": len(stdout),
        "raw_stdout_sha256": sha256_bytes(stdout),
        "stderr_byte_count": len(stderr),
        "stderr_sha256": sha256_bytes(stderr),
        "max_budget_usd": args.max_budget_usd,
    }
    try:
        if result.returncode:
            raise CritiqueError(f"Claude CLI exited with {result.returncode}")
        wrapper = json.loads(result.stdout)
        event = result_event(wrapper)
        public["reported_total_cost_usd"] = event.get("total_cost_usd")
        public["reported_model_usage"] = public_model_usage(event)
        public["wrapper_metadata"] = {
            key: event.get(key)
            for key in (
                "subtype",
                "is_error",
                "duration_ms",
                "duration_api_ms",
                "num_turns",
                "stop_reason",
            )
        }
        critique = event.get("structured_output")
        if not isinstance(critique, dict):
            result_text = event.get("result")
            if isinstance(result_text, str):
                critique = json.loads(result_text)
        if not isinstance(critique, dict):
            raise CritiqueError("Fable returned no structured critique")
        validate_critique(critique)
        write_new_json(args.trace_root / "parsed-critique.json", critique)
        public["critique"] = critique
        public["status"] = "completed_valid"
    except Exception as error:
        failure = f"{type(error).__name__}: {error}"
        write_new_bytes(args.trace_root / "failure.txt", failure.encode())
        public["failure"] = failure
        public["failure_sha256"] = sha256_bytes(failure.encode())

    write_new_json(args.trace_root / "attempt-complete.json", public)
    write_new_json(args.public_result, public)
    append_event(
        event_log,
        "fable_pipeline_critique_completed",
        run_id=args.run_id,
        status=public["status"],
        retry_allowed=False,
    )
    print(
        "FABLE_PIPELINE_CRITIQUE_COMPLETE "
        f"run_id={args.run_id} status={public['status']} "
        f"cost_usd={public.get('reported_total_cost_usd')}"
    )
    return 0 if public["status"] == "completed_valid" else 4


if __name__ == "__main__":
    raise SystemExit(main())
