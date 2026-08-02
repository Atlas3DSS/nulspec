#!/usr/bin/env python3
"""Build and execute the one-shot Fable final peer-review gate."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time
from typing import Any


PACKET_SCHEMA = "nulspec-fable-final-review-packet-v1"
RESULT_SCHEMA = "nulspec-fable-final-peer-review-v1"
CLOSURE_SCHEMA = "nulspec-fable-action-closure-v1"
EMAIL_APPROVAL_SCHEMA = "nulspec-author-email-human-approval-v1"
SUPPLEMENTAL_CONSENSUS_SCHEMA = "nulspec-supplemental-review-consensus-v1"
PROTOCOL_ID = "nulspec-fable-one-shot-final-gate-v1"
EXPECTED_SEEDS = list(range(5))
EXPECTED_AREAS = {
    "scientific_fidelity",
    "internal_consistency",
    "statistics_and_uncertainty",
    "replication_extension_boundary",
    "reproducibility_and_provenance",
    "error_transparency",
    "publication_handoff",
    "author_email_fairness",
}
DOCUMENTS = (
    "ONE_PAGE.md",
    "REPORT.md",
    "PROTOCOL.md",
    "EXTENSION_PROTOCOL.md",
    "POSTHOC_DIAGNOSTICS.md",
    "UPSTREAM_AUDIT.md",
    "ERROR_LOG.md",
    "TESTS.md",
    "SOURCE_MANIFEST.md",
    "CITATION_AUDIT.md",
    "FRONTEND_HANDOFF.md",
    "AUTHOR_QUESTIONS.md",
    "AUTHOR_EMAIL.md",
    "CONTAINER.md",
    "FABLE_REVIEW_PROTOCOL.md",
)
WEBSITE_HANDOFF = "WEBSITE_HANDOFF.json"
RESULT_INPUTS = {
    "primary": (
        "results/scratch_summary.json",
        "nulspec-sprkd-aggregate-v1",
    ),
    "extensions": (
        "results/extension_summary.json",
        "nulspec-sprkd-extension-aggregate-v1",
    ),
    "hessian": (
        "results/hessian_extension_summary.json",
        "nulspec-sprkd-hessian-aggregate-v1",
    ),
    "stability": (
        "results/training_stability_summary.json",
        "nulspec-sprkd-posthoc-stability-v1",
    ),
    "loss_contract": (
        "results/loss_contract_extension_summary.json",
        "nulspec-sprkd-loss-contract-aggregate-v1",
    ),
    "released_artifacts": (
        "results/released_artifact_verification.json",
        "nulspec-sprkd-released-verification-v2",
    ),
    "citations": (
        "results/citation_audit_results.json",
        "nulspec-sprkd-citation-audit-summary-v2",
    ),
}

SYSTEM_PROMPT = (
    "You are Fable, the final independent peer reviewer for a small scientific "
    "replication team. You are a release judge, not a coauthor. Work only from "
    "the committed evidence packet supplied by the user. Do not use tools, "
    "invent missing evidence, rewrite results, or optimize for agreement. "
    "Return only the requested structured output."
)

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "reviewed_packet_sha256",
        "verdict",
        "summary",
        "checks",
        "action_items",
        "hard_fail_reason",
        "human_review_required",
        "next_step",
        "single_review_acknowledged",
        "no_resubmission_acknowledged",
        "human_email_approval_acknowledged",
    ],
    "properties": {
        "reviewed_packet_sha256": {
            "type": "string",
            "pattern": "^[0-9a-f]{64}$",
        },
        "verdict": {"enum": ["PASS", "FAIL", "HARD_FAIL"]},
        "summary": {"type": "string", "minLength": 1},
        "checks": {
            "type": "array",
            "minItems": 8,
            "maxItems": 8,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["area", "status", "finding", "evidence"],
                "properties": {
                    "area": {"enum": sorted(EXPECTED_AREAS)},
                    "status": {"enum": ["PASS", "FAIL"]},
                    "finding": {"type": "string", "minLength": 1},
                    "evidence": {"type": "string", "minLength": 1},
                },
            },
        },
        "action_items": {
            "type": "array",
            "maxItems": 3,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "id",
                    "title",
                    "required_change",
                    "acceptance_test",
                ],
                "properties": {
                    "id": {"enum": ["F1", "F2", "F3"]},
                    "title": {"type": "string", "minLength": 1},
                    "required_change": {"type": "string", "minLength": 1},
                    "acceptance_test": {"type": "string", "minLength": 1},
                },
            },
        },
        "hard_fail_reason": {"type": "string"},
        "human_review_required": {"type": "boolean"},
        "next_step": {
            "enum": [
                "PUBLISH_AND_QUEUE_AUTHOR_EMAIL_FOR_HUMAN_APPROVAL",
                "FIX_THREE_ACTIONS_THEN_PUBLISH_NO_RESUBMISSION_QUEUE_EMAIL_FOR_HUMAN_APPROVAL",
                "STOP_FOR_HUMAN_REVIEW",
            ]
        },
        "single_review_acknowledged": {"type": "boolean"},
        "no_resubmission_acknowledged": {"type": "boolean"},
        "human_email_approval_acknowledged": {"type": "boolean"},
    },
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object: {path}")
    return payload


def validate_sources(loaded: dict[str, dict[str, Any]]) -> None:
    for name, (_, schema) in RESULT_INPUTS.items():
        if loaded[name].get("schema_version") != schema:
            raise ValueError(f"{name}: unexpected schema")
    for name in ("primary", "extensions", "hessian", "stability", "loss_contract"):
        payload = loaded[name]
        if payload.get("status") != "complete":
            raise ValueError(f"{name}: aggregate is incomplete")
        if payload.get("complete_seeds") != EXPECTED_SEEDS:
            raise ValueError(f"{name}: frozen seeds differ")
    if loaded["citations"].get("target_arxiv_id") != "2607.23346v1":
        raise ValueError("citation audit targets a different paper")


def compact_hessian(payload: dict[str, Any]) -> dict[str, Any]:
    compact = deepcopy(payload)
    probe_records = []
    for run in compact["runs"]:
        seed = int(run["seed"])
        for model_name, model in run["models"].items():
            values = model.pop("probe_values")
            if len(values) != 100 or not all(math.isfinite(float(x)) for x in values):
                raise ValueError(f"seed {seed} {model_name}: invalid Hessian probes")
            record = {
                "seed": seed,
                "model": model_name,
                "values": values,
            }
            model["probe_values_sha256"] = sha256_bytes(canonical_json(record))
            probe_records.append(record)
    if len(probe_records) != 25:
        raise ValueError("Hessian packet does not cover 25 seed/model records")
    compact["raw_probe_evidence"] = {
        "records": 25,
        "values_per_record": 100,
        "total_values": 2500,
        "canonical_sha256": sha256_bytes(canonical_json(probe_records)),
        "source_file_sha256": sha256(Path(payload["_source_path"]))
        if "_source_path" in payload
        else None,
    }
    compact.pop("_source_path", None)
    return compact


def compact_website_handoff(payload: dict[str, Any]) -> dict[str, Any]:
    """Retain the handoff contract while hashing duplicated diagnostic rows."""
    compact = deepcopy(payload)
    if compact.get("schema_version") != (
        "nulspec-classification-accuracy-study-handoff-v1"
    ):
        raise ValueError("website handoff uses an unexpected schema")
    gate = compact.get("publication_status", {}).get("research_release_gate", {})
    if gate.get("status") != "blocked_pending_fable_one_shot_review":
        raise ValueError("review packet requires the pending pre-review handoff")
    if gate.get("publication_authorized") is not False:
        raise ValueError("pre-review handoff unexpectedly authorizes publication")
    for name in (
        "preregistered_extensions",
        "common_probe_hessian",
        "posthoc_loss_contract",
    ):
        diagnostic = compact["diagnostics"][name]
        rows = diagnostic.pop("runs")
        diagnostic["run_evidence"] = {
            "records": len(rows),
            "canonical_sha256": sha256_bytes(canonical_json(rows)),
            "omission_reason": (
                "Rows duplicate the separately included validated machine evidence."
            ),
        }
    return compact


def build_packet(study_root: Path) -> dict[str, Any]:
    root = study_root.resolve()
    loaded = {
        name: load_json(root / relative)
        for name, (relative, _) in RESULT_INPUTS.items()
    }
    validate_sources(loaded)
    hessian_source = root / RESULT_INPUTS["hessian"][0]
    loaded["hessian"]["_source_path"] = str(hessian_source)

    documents = {}
    input_hashes = {}
    for relative in DOCUMENTS:
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        documents[relative] = path.read_text()
        input_hashes[relative] = sha256(path)
    for relative, _ in RESULT_INPUTS.values():
        input_hashes[relative] = sha256(root / relative)
    handoff_path = root / WEBSITE_HANDOFF
    handoff = load_json(handoff_path)
    input_hashes[WEBSITE_HANDOFF] = sha256(handoff_path)
    for relative in ("scripts/fable_final_review.py",):
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        input_hashes[relative] = sha256(path)

    machine_evidence = {
        "primary": loaded["primary"],
        "preregistered_extensions": loaded["extensions"],
        "common_probe_hessian": compact_hessian(loaded["hessian"]),
        "posthoc_stability": loaded["stability"],
        "posthoc_loss_contract": loaded["loss_contract"],
        "released_artifacts": loaded["released_artifacts"],
        "citation_audit": loaded["citations"],
        "website_handoff_candidate": compact_website_handoff(handoff),
    }
    return {
        "schema_version": PACKET_SCHEMA,
        "protocol": PROTOCOL_ID,
        "study": {
            "id": "260723346",
            "arxiv_id": "2607.23346v1",
            "scope": "Experiment 1 malaria classification",
            "frozen_replication_outcome": "not_replicated",
            "frozen_underlying_method_claim": "inconclusive",
        },
        "decision_contract": {
            "one_invocation_only": True,
            "resubmission_allowed": False,
            "PASS": (
                "Publish, then queue the author-email draft for mandatory "
                "human approval. Fable cannot authorize dispatch."
            ),
            "FAIL": (
                "Return exactly three actions. Research closes all three, "
                "then publishes without resubmission and queues the author-email "
                "draft for mandatory human approval."
            ),
            "HARD_FAIL": (
                "Stop publication and the author-email workflow for human review."
            ),
        },
        "review_criteria": sorted(EXPECTED_AREAS),
        "input_sha256s": dict(sorted(input_hashes.items())),
        "documents": documents,
        "machine_evidence": machine_evidence,
    }


def prompt_for_packet(packet_text: str, packet_sha256: str) -> str:
    return f"""Conduct the one-shot final peer review described below.

This is your only review of this release candidate. There will be no
resubmission to you. Your decision must obey exactly one branch:

- PASS: the bundle is scientifically honest, internally consistent,
  reproducible within its disclosed boundary, fair to the authors, and ready
  to publish. Return zero action items. This makes the author-email draft
  eligible for separate human approval; it does not authorize dispatch.
- FAIL: the bundle can be made publishable through concrete corrections.
  Return exactly three action items, IDs F1, F2, and F3. After research closes
  them, it will publish without asking you again. The author-email draft then
  becomes eligible for separate human approval.
- HARD_FAIL: responsible publication requires human judgment or cannot be
  reduced to exactly three corrections. Return zero action items and a precise
  hard-fail reason. Publication and author email stop for a human.

Do not change the frozen numerical results or reward favorable findings. Check
the prose against machine evidence, statistical language, replication versus
extension/post-hoc boundaries, provenance, error transparency, website
handoff, and the author-email draft. A limitation that is already candidly
disclosed is not automatically a failure. Required corrections must improve
truthfulness, reproducibility, or fairness.

The author email is downstream of your gate but always requires a final human
approval. Neither PASS nor a closed FAIL authorizes dispatch; each only makes
the exact draft eligible for human approval. HARD_FAIL stops that workflow.
Explicitly acknowledge the single-review, no-resubmission, and mandatory human
email-approval rules in the structured response.

Set reviewed_packet_sha256 to exactly:
{packet_sha256}

COMMITTED REVIEW PACKET:
{packet_text}
"""


def result_wrapper(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, list):
        for item in reversed(payload):
            if isinstance(item, dict) and item.get("type") == "result":
                return item
    raise ValueError("Claude output did not contain a result wrapper")


def parse_structured(wrapper: dict[str, Any]) -> dict[str, Any]:
    value = wrapper.get("structured_output")
    if isinstance(value, dict):
        return value
    result = wrapper.get("result")
    if isinstance(result, dict):
        return result
    if isinstance(result, str):
        parsed = json.loads(result)
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("Claude output did not contain structured JSON")


def validate_decision(decision: dict[str, Any], packet_sha256: str) -> None:
    if decision.get("reviewed_packet_sha256") != packet_sha256:
        raise ValueError("Fable returned a different packet digest")
    verdict = decision.get("verdict")
    if verdict not in {"PASS", "FAIL", "HARD_FAIL"}:
        raise ValueError("invalid Fable verdict")
    checks = decision.get("checks")
    if not isinstance(checks, list) or len(checks) != len(EXPECTED_AREAS):
        raise ValueError("Fable did not return eight checks")
    areas = [row.get("area") for row in checks if isinstance(row, dict)]
    if set(areas) != EXPECTED_AREAS or len(areas) != len(set(areas)):
        raise ValueError("Fable check areas are incomplete or duplicated")
    statuses = [row.get("status") for row in checks]
    if not all(status in {"PASS", "FAIL"} for status in statuses):
        raise ValueError("invalid check status")
    actions = decision.get("action_items")
    if not isinstance(actions, list):
        raise ValueError("action_items is not an array")
    action_ids = [row.get("id") for row in actions if isinstance(row, dict)]
    hard_reason = str(decision.get("hard_fail_reason") or "").strip()
    expected = {
        "PASS": (
            0,
            False,
            "PUBLISH_AND_QUEUE_AUTHOR_EMAIL_FOR_HUMAN_APPROVAL",
        ),
        "FAIL": (
            3,
            False,
            "FIX_THREE_ACTIONS_THEN_PUBLISH_NO_RESUBMISSION_QUEUE_EMAIL_FOR_HUMAN_APPROVAL",
        ),
        "HARD_FAIL": (0, True, "STOP_FOR_HUMAN_REVIEW"),
    }[verdict]
    if len(actions) != expected[0]:
        raise ValueError(f"{verdict} returned the wrong action count")
    if verdict == "FAIL" and action_ids != ["F1", "F2", "F3"]:
        raise ValueError("FAIL actions must be ordered F1, F2, F3")
    if bool(decision.get("human_review_required")) is not expected[1]:
        raise ValueError(f"{verdict} has the wrong human-review flag")
    if decision.get("next_step") != expected[2]:
        raise ValueError(f"{verdict} has the wrong next step")
    if verdict == "PASS" and any(status != "PASS" for status in statuses):
        raise ValueError("PASS contains a failed check")
    if verdict in {"FAIL", "HARD_FAIL"} and "FAIL" not in statuses:
        raise ValueError(f"{verdict} does not identify a failed check")
    if verdict == "HARD_FAIL" and not hard_reason:
        raise ValueError("HARD_FAIL omitted its reason")
    if verdict != "HARD_FAIL" and hard_reason:
        raise ValueError(f"{verdict} unexpectedly included a hard-fail reason")
    for key in (
        "single_review_acknowledged",
        "no_resubmission_acknowledged",
        "human_email_approval_acknowledged",
    ):
        if decision.get(key) is not True:
            raise ValueError(f"Fable did not acknowledge {key}")


def repository_root(study_root: Path) -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=study_root,
        text=True,
        capture_output=True,
        check=True,
    )
    return Path(result.stdout.strip()).resolve()


def resolve_study_path(study_root: Path, value: Path) -> Path:
    return value.resolve() if value.is_absolute() else (study_root / value).resolve()


def reviewed_commit(study_root: Path, packet: Path) -> str:
    repo = repository_root(study_root)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    relative_packet = packet.resolve().relative_to(repo)
    committed = subprocess.run(
        ["git", "show", f"HEAD:{relative_packet.as_posix()}"],
        cwd=repo,
        capture_output=True,
        check=True,
    ).stdout
    if committed != packet.read_bytes():
        raise RuntimeError("review packet differs from the committed blob")
    relative_study = study_root.resolve().relative_to(repo)
    diff = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", relative_study.as_posix()],
        cwd=repo,
        check=False,
    )
    if diff.returncode != 0:
        raise RuntimeError("study tree differs from the committed candidate")
    untracked = subprocess.run(
        [
            "git",
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            relative_study.as_posix(),
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    if untracked:
        raise RuntimeError("study tree contains untracked publishable files")
    return commit


def technical_decision(packet_sha256: str, reason: str) -> dict[str, Any]:
    return {
        "reviewed_packet_sha256": packet_sha256,
        "verdict": "HARD_FAIL",
        "summary": "The one-shot final review did not yield a valid decision.",
        "checks": [
            {
                "area": area,
                "status": "FAIL",
                "finding": "No valid Fable decision was available.",
                "evidence": "The retained invocation record contains the failure.",
            }
            for area in sorted(EXPECTED_AREAS)
        ],
        "action_items": [],
        "hard_fail_reason": reason,
        "human_review_required": True,
        "next_step": "STOP_FOR_HUMAN_REVIEW",
        "single_review_acknowledged": True,
        "no_resubmission_acknowledged": True,
        "human_email_approval_acknowledged": True,
    }


def render_markdown(result: dict[str, Any]) -> str:
    decision = result["decision"]
    lines = [
        "# Fable final peer review",
        "",
        f"**Verdict:** **{decision['verdict']}**",
        "",
        decision["summary"],
        "",
        "This is the single permitted Fable review for this release candidate. "
        "It is a publication gate, not evidence for or against the paper's method.",
        "",
        "## Review checks",
        "",
        "| Area | Status | Finding | Evidence |",
        "|---|---|---|---|",
    ]
    for row in decision["checks"]:
        values = [
            str(row[key]).replace("|", "\\|").replace("\n", " ")
            for key in ("area", "status", "finding", "evidence")
        ]
        lines.append("| " + " | ".join(values) + " |")
    lines.extend(["", "## Required actions", ""])
    if decision["action_items"]:
        for item in decision["action_items"]:
            lines.extend(
                [
                    f"### {item['id']} — {item['title']}",
                    "",
                    f"Required change: {item['required_change']}",
                    "",
                    f"Acceptance test: {item['acceptance_test']}",
                    "",
                ]
            )
    else:
        lines.append("None.")
        lines.append("")
    if decision["hard_fail_reason"]:
        lines.extend(["## Human-review reason", "", decision["hard_fail_reason"], ""])
    gate = result["gate"]
    lines.extend(
        [
            "## Release gate",
            "",
            f"- Status: `{gate['status']}`",
            f"- Publication authorized: `{str(gate['publication_authorized']).lower()}`",
            "- Author email eligible for human approval: "
            f"`{str(gate['author_email_eligible_for_human_approval']).lower()}`",
            "- Author email dispatch authorized: "
            f"`{str(gate['author_email_dispatch_authorized']).lower()}`",
            "- Final human email approval required: `true`",
            f"- Human review required: `{str(gate['human_review_required']).lower()}`",
            "- Resubmission to Fable: `forbidden`",
            "",
            "## Provenance",
            "",
            f"- Reviewed commit: `{result['reviewed_commit']}`",
            f"- Packet SHA-256: `{result['packet']['sha256']}`",
            f"- Prompt SHA-256: `{result['invocation']['prompt_sha256']}`",
            f"- Raw response SHA-256: `{result['invocation']['raw_response_sha256']}`",
            "- Full raw trace: retained in the ignored lab archive",
            "",
        ]
    )
    return "\n".join(lines)


def initial_gate(decision: dict[str, Any]) -> dict[str, Any]:
    verdict = decision["verdict"]
    if verdict == "PASS":
        return {
            "status": "approved",
            "publication_authorized": True,
            "author_email_eligible_for_human_approval": True,
            "author_email_dispatch_authorized": False,
            "author_email_human_approval_required": True,
            "author_email_approval_status": "pending_final_human_approval",
            "human_review_required": False,
            "action_closure_required": False,
        }
    if verdict == "FAIL":
        return {
            "status": "blocked_pending_three_action_closure",
            "publication_authorized": False,
            "author_email_eligible_for_human_approval": False,
            "author_email_dispatch_authorized": False,
            "author_email_human_approval_required": True,
            "author_email_approval_status": "blocked_pending_action_closure",
            "human_review_required": False,
            "action_closure_required": True,
        }
    return {
        "status": "blocked_pending_human_review",
        "publication_authorized": False,
        "author_email_eligible_for_human_approval": False,
        "author_email_dispatch_authorized": False,
        "author_email_human_approval_required": True,
        "author_email_approval_status": "blocked_pending_hard_fail_human_review",
        "human_review_required": True,
        "action_closure_required": False,
    }


def run_review_once(args: argparse.Namespace) -> int:
    study_root = args.study_root.resolve()
    packet = resolve_study_path(study_root, args.packet)
    output_root = resolve_study_path(study_root, args.output_root)
    public_result_path = resolve_study_path(study_root, args.public_result)
    markdown_path = resolve_study_path(study_root, args.markdown)
    attempt_path = output_root / "attempt.json"
    if attempt_path.exists():
        raise RuntimeError(
            "one-shot attempt marker already exists; resubmission is forbidden"
        )
    commit = reviewed_commit(study_root, packet)
    packet_bytes = packet.read_bytes()
    packet_sha = sha256_bytes(packet_bytes)
    packet_payload = json.loads(packet_bytes)
    if packet_payload.get("schema_version") != PACKET_SCHEMA:
        raise ValueError("unexpected review packet schema")
    prompt = prompt_for_packet(packet_bytes.decode(), packet_sha)
    output_root.mkdir(parents=True, exist_ok=True)
    prompt_path = output_root / "prompt.txt"
    raw_path = output_root / "raw.json"
    stderr_path = output_root / "stderr.txt"
    prompt_path.write_text(prompt)
    started_at = now()
    attempt = {
        "schema_version": "nulspec-fable-one-shot-attempt-v1",
        "protocol": PROTOCOL_ID,
        "status": "started",
        "started_at_utc": started_at,
        "reviewed_commit": commit,
        "packet_sha256": packet_sha,
        "prompt_sha256": sha256_bytes(prompt.encode()),
        "invocation_count": 1,
        "resubmission_allowed": False,
    }
    attempt_path.write_text(json.dumps(attempt, indent=2, sort_keys=True) + "\n")

    environment = os.environ.copy()
    environment.pop("ANTHROPIC_API_KEY", None)
    command = [
        "claude",
        "--safe-mode",
        "--tools",
        "",
        "--model",
        "fable",
        "--effort",
        "max",
        "--print",
        "--no-session-persistence",
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(OUTPUT_SCHEMA, separators=(",", ":")),
        "--system-prompt",
        SYSTEM_PROMPT,
    ]
    start = time.monotonic()
    invocation_failure = ""
    process_exit_code: int | None = None
    stdout = ""
    stderr = ""
    try:
        process = subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            check=False,
            env=environment,
            timeout=1800,
        )
        process_exit_code = process.returncode
        stdout = process.stdout
        stderr = process.stderr
    except subprocess.TimeoutExpired as error:
        invocation_failure = "TimeoutExpired: Fable invocation exceeded 1800 seconds"
        stdout = error.stdout or ""
        stderr = error.stderr or ""
    except OSError as error:
        invocation_failure = f"{type(error).__name__}: {error}"
    elapsed = time.monotonic() - start
    if isinstance(stdout, bytes):
        stdout = stdout.decode(errors="replace")
    if isinstance(stderr, bytes):
        stderr = stderr.decode(errors="replace")
    raw_path.write_text(stdout)
    stderr_path.write_text(stderr)
    completed_at = now()
    wrapper: dict[str, Any] = {}
    failure = invocation_failure
    try:
        if failure:
            raise RuntimeError(failure)
        wrapper = result_wrapper(json.loads(stdout))
        if process_exit_code:
            raise RuntimeError(f"Claude CLI exited {process_exit_code}")
        if wrapper.get("is_error"):
            raise RuntimeError(str(wrapper.get("result") or "Claude error"))
        if wrapper.get("stop_reason") == "refusal":
            raise RuntimeError("Fable safeguard refusal")
        decision = parse_structured(wrapper)
        validate_decision(decision, packet_sha)
        decision_source = "fable_structured_output"
    except Exception as error:
        failure = f"{type(error).__name__}: {error}"
        decision = technical_decision(packet_sha, failure)
        decision_source = "technical_failure_fail_closed"

    attempt.update(
        {
            "status": "completed_valid" if not failure else "completed_hard_fail",
            "completed_at_utc": completed_at,
            "process_exit_code": process_exit_code,
            "elapsed_seconds": round(elapsed, 6),
            "raw_response_sha256": sha256(raw_path),
            "stderr_sha256": sha256(stderr_path),
            "technical_failure": failure or None,
        }
    )
    attempt_path.write_text(json.dumps(attempt, indent=2, sort_keys=True) + "\n")
    wrapper_metadata = {
        key: wrapper.get(key)
        for key in (
            "is_error",
            "stop_reason",
            "terminal_reason",
            "duration_ms",
            "duration_api_ms",
            "num_turns",
            "total_cost_usd",
            "usage",
            "modelUsage",
        )
        if key in wrapper
    }
    public_result = {
        "schema_version": RESULT_SCHEMA,
        "protocol": PROTOCOL_ID,
        "single_invocation": True,
        "resubmission_allowed": False,
        "reviewed_commit": commit,
        "started_at_utc": started_at,
        "completed_at_utc": completed_at,
        "packet": {
            "path": str(args.packet),
            "sha256": packet_sha,
            "bytes": len(packet_bytes),
        },
        "reviewer": {
            "identity": "Fable",
            "model_alias": "fable",
            "effort": "max",
            "tools_enabled": False,
            "authentication": "existing_subscription",
        },
        "invocation": {
            "process_exit_code": process_exit_code,
            "elapsed_seconds": round(elapsed, 6),
            "prompt_sha256": sha256_bytes(prompt.encode()),
            "raw_response_sha256": sha256(raw_path),
            "stderr_sha256": sha256(stderr_path),
            "raw_trace_public": False,
            "raw_trace_retention": "ignored_lab_archive",
            "wrapper_metadata": wrapper_metadata,
            "technical_failure": failure or None,
        },
        "decision_source": decision_source,
        "decision": decision,
        "gate": initial_gate(decision),
    }
    public_result_path.parent.mkdir(parents=True, exist_ok=True)
    public_result_path.write_text(
        json.dumps(public_result, indent=2, sort_keys=True) + "\n"
    )
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(public_result))
    print(
        f"FABLE_FINAL_REVIEW verdict={decision['verdict']} "
        f"gate={public_result['gate']['status']} commit={commit}",
        flush=True,
    )
    return 0 if not failure else 4


def evaluate_gate(
    review: dict[str, Any], closure: dict[str, Any] | None
) -> dict[str, Any]:
    if review.get("schema_version") != RESULT_SCHEMA:
        raise ValueError("unexpected Fable result schema")
    if review.get("single_invocation") is not True:
        raise ValueError("Fable result does not prove a single invocation")
    if review.get("resubmission_allowed") is not False:
        raise ValueError("Fable result permits resubmission")
    decision = review["decision"]
    validate_decision(decision, review["packet"]["sha256"])
    verdict = decision["verdict"]
    if verdict == "PASS":
        if closure is not None:
            raise ValueError("PASS must not have an action closure")
        return initial_gate(decision)
    if verdict == "HARD_FAIL":
        return initial_gate(decision)
    if closure is None:
        return initial_gate(decision)
    if closure.get("schema_version") != CLOSURE_SCHEMA:
        raise ValueError("unexpected Fable action-closure schema")
    if closure.get("review_sha256") != sha256_bytes(canonical_json(review)):
        raise ValueError("action closure binds a different review")
    if closure.get("no_resubmission_performed") is not True:
        raise ValueError("action closure does not affirm no resubmission")
    items = closure.get("actions")
    if not isinstance(items, list) or [row.get("id") for row in items] != [
        "F1",
        "F2",
        "F3",
    ]:
        raise ValueError("action closure must preserve F1, F2, F3")
    for row in items:
        if row.get("status") != "RESOLVED":
            raise ValueError(f"{row.get('id')}: action is not resolved")
        if not str(row.get("implemented_change") or "").strip():
            raise ValueError(f"{row.get('id')}: missing implemented change")
        evidence = row.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"{row.get('id')}: missing resolution evidence")
    return {
        "status": "approved_after_three_action_closure",
        "publication_authorized": True,
        "author_email_eligible_for_human_approval": True,
        "author_email_dispatch_authorized": False,
        "author_email_human_approval_required": True,
        "author_email_approval_status": "pending_final_human_approval",
        "human_review_required": False,
        "action_closure_required": False,
    }


def validate_email_approval(
    approval: dict[str, Any],
    author_email_sha256: str,
    review: dict[str, Any],
    closure: dict[str, Any] | None,
    supplemental_consensus_sha256: str | None = None,
) -> None:
    if approval.get("schema_version") != EMAIL_APPROVAL_SCHEMA:
        raise ValueError("unexpected author-email human-approval schema")
    if approval.get("decision") != "APPROVE_SEND":
        raise ValueError("author-email record does not approve dispatch")
    if approval.get("human_approved") is not True:
        raise ValueError("author-email record lacks explicit human approval")
    if approval.get("exact_draft_only") is not True:
        raise ValueError("author-email approval is not limited to the exact draft")
    if not str(approval.get("approved_at_utc") or "").strip():
        raise ValueError("author-email approval lacks a timestamp")
    if approval.get("author_email_sha256") != author_email_sha256:
        raise ValueError("author-email approval binds a different draft")
    if approval.get("final_peer_review_sha256") != sha256_bytes(canonical_json(review)):
        raise ValueError("author-email approval binds a different final review")
    closure_sha = sha256_bytes(canonical_json(closure)) if closure else None
    if approval.get("fable_action_closure_sha256") != closure_sha:
        raise ValueError("author-email approval binds a different action closure")
    if (
        approval.get("supplemental_review_consensus_sha256")
        != supplemental_consensus_sha256
    ):
        raise ValueError("author-email approval binds a different supplemental review")


def evaluate_supplemental_consensus(
    consensus: dict[str, Any],
    *,
    fable_result_sha256: str,
    packet_sha256: str,
) -> dict[str, Any]:
    if consensus.get("schema_version") != SUPPLEMENTAL_CONSENSUS_SCHEMA:
        raise ValueError("unexpected supplemental-review consensus schema")
    if consensus.get("source_fable_result_sha256") != fable_result_sha256:
        raise ValueError("supplemental consensus binds a different Fable result")
    binding = consensus.get("binding")
    if not isinstance(binding, dict) or binding.get("packet_sha256") != packet_sha256:
        raise ValueError("supplemental consensus binds a different packet")
    policy = consensus.get("policy")
    if not isinstance(policy, dict):
        raise ValueError("supplemental consensus lacks its policy")
    required_policy = {
        "required_reviewers": ["GLM", "Kimi"],
        "same_immutable_packet_required": True,
        "both_structured_pass_required": True,
        "malformed_refusal_or_non_pass_fails_closed": True,
        "retry_or_tiebreaker_allowed": False,
        "scientific_result_mutable": False,
        "author_email_dispatch_requires_separate_human_approval": True,
    }
    for key, expected in required_policy.items():
        if policy.get(key) != expected:
            raise ValueError(f"supplemental policy differs at {key}")
    pair = consensus.get("primary_pair")
    if not isinstance(pair, list) or len(pair) != 2:
        raise ValueError(
            "supplemental consensus must contain exactly two primary reviews"
        )
    if [row.get("reviewer_family") for row in pair] != ["GLM", "Kimi"]:
        raise ValueError("supplemental reviewers differ or are reordered")
    if not all(row.get("consensus_eligible") is True for row in pair):
        raise ValueError("supplemental primary pair contains an ineligible review")
    both_valid_pass = all(
        row.get("structured_valid") is True and row.get("validated_verdict") == "PASS"
        for row in pair
    )
    decision = consensus.get("decision")
    if decision == "PASS":
        if not both_valid_pass:
            raise ValueError(
                "supplemental PASS lacks two valid structured PASS reviews"
            )
        if consensus.get("publication_authorized") is not True:
            raise ValueError("supplemental PASS does not authorize publication")
        if consensus.get("author_email_dispatch_authorized") is not False:
            raise ValueError("supplemental PASS incorrectly authorizes email dispatch")
        if consensus.get("author_email_human_approval_required") is not True:
            raise ValueError("supplemental PASS drops mandatory human email approval")
        return {
            "status": "approved_by_glm_kimi_consensus_after_fable_hard_fail",
            "publication_authorized": True,
            "author_email_eligible_for_human_approval": True,
            "author_email_dispatch_authorized": False,
            "author_email_human_approval_required": True,
            "author_email_approval_status": "pending_final_human_approval",
            "human_review_required": False,
            "action_closure_required": False,
            "supplemental_review_decision": "PASS",
        }
    if decision != "HARD_FAIL":
        raise ValueError("supplemental decision must be PASS or HARD_FAIL")
    if both_valid_pass:
        raise ValueError("supplemental HARD_FAIL contradicts two valid PASS reviews")
    for key in (
        "publication_authorized",
        "author_email_eligible_for_human_approval",
        "author_email_dispatch_authorized",
    ):
        if consensus.get(key) is not False:
            raise ValueError(f"supplemental HARD_FAIL opened {key}")
    if consensus.get("human_review_required") is not True:
        raise ValueError("supplemental HARD_FAIL does not require human review")
    if consensus.get("author_email_human_approval_required") is not True:
        raise ValueError("supplemental HARD_FAIL drops mandatory human email approval")
    return {
        "status": "blocked_after_supplemental_hard_fail_pending_human_review",
        "publication_authorized": False,
        "author_email_eligible_for_human_approval": False,
        "author_email_dispatch_authorized": False,
        "author_email_human_approval_required": True,
        "author_email_approval_status": (
            "blocked_pending_supplemental_hard_fail_human_review"
        ),
        "human_review_required": True,
        "action_closure_required": False,
        "supplemental_review_decision": "HARD_FAIL",
    }


def gate_for_paths(study_root: Path) -> dict[str, Any]:
    result_path = study_root / "results/fable_final_peer_review.json"
    if not result_path.is_file():
        premature = [
            path
            for path in (
                study_root / "results/fable_action_closure.json",
                study_root / "results/author_email_human_approval.json",
                study_root / "FABLE_FINAL_REVIEW.md",
            )
            if path.exists()
        ]
        if premature:
            raise ValueError("downstream review artifacts exist before Fable review")
        return {
            "status": "blocked_pending_fable_one_shot_review",
            "publication_authorized": False,
            "author_email_eligible_for_human_approval": False,
            "author_email_dispatch_authorized": False,
            "author_email_human_approval_required": True,
            "author_email_approval_status": "blocked_pending_fable_review",
            "human_review_required": False,
            "action_closure_required": False,
        }
    review = load_json(result_path)
    closure_path = study_root / "results/fable_action_closure.json"
    closure = load_json(closure_path) if closure_path.is_file() else None
    gate = evaluate_gate(review, closure)
    supplemental_path = study_root / "results/supplemental_review_consensus.json"
    supplemental_sha256 = None
    if supplemental_path.is_file():
        if review["decision"]["verdict"] != "HARD_FAIL":
            raise ValueError("supplemental consensus exists without a Fable HARD_FAIL")
        supplemental = load_json(supplemental_path)
        supplemental_sha256 = sha256(supplemental_path)
        gate = evaluate_supplemental_consensus(
            supplemental,
            fable_result_sha256=sha256(result_path),
            packet_sha256=review["packet"]["sha256"],
        )
    approval_path = study_root / "results/author_email_human_approval.json"
    if not approval_path.is_file():
        return gate
    if not gate["author_email_eligible_for_human_approval"]:
        raise ValueError("author-email approval exists before the draft is eligible")
    approval = load_json(approval_path)
    validate_email_approval(
        approval,
        sha256(study_root / "AUTHOR_EMAIL.md"),
        review,
        closure,
        supplemental_sha256,
    )
    gate["author_email_dispatch_authorized"] = True
    gate["author_email_approval_status"] = "approved_for_exact_draft_once"
    return gate


def self_test() -> None:
    packet_sha = "a" * 64
    base = {
        "reviewed_packet_sha256": packet_sha,
        "verdict": "PASS",
        "summary": "Ready.",
        "checks": [
            {
                "area": area,
                "status": "PASS",
                "finding": "No blocking issue.",
                "evidence": "Synthetic test evidence.",
            }
            for area in sorted(EXPECTED_AREAS)
        ],
        "action_items": [],
        "hard_fail_reason": "",
        "human_review_required": False,
        "next_step": "PUBLISH_AND_QUEUE_AUTHOR_EMAIL_FOR_HUMAN_APPROVAL",
        "single_review_acknowledged": True,
        "no_resubmission_acknowledged": True,
        "human_email_approval_acknowledged": True,
    }
    validate_decision(base, packet_sha)
    failed = deepcopy(base)
    failed.update(
        {
            "verdict": "FAIL",
            "next_step": (
                "FIX_THREE_ACTIONS_THEN_PUBLISH_NO_RESUBMISSION_QUEUE_EMAIL_FOR_HUMAN_APPROVAL"
            ),
            "action_items": [
                {
                    "id": f"F{index}",
                    "title": f"Action {index}",
                    "required_change": "Correct the record.",
                    "acceptance_test": "The deterministic check passes.",
                }
                for index in range(1, 4)
            ],
        }
    )
    failed["checks"][0]["status"] = "FAIL"
    validate_decision(failed, packet_sha)
    hard = deepcopy(base)
    hard.update(
        {
            "verdict": "HARD_FAIL",
            "hard_fail_reason": "Human judgment is required.",
            "human_review_required": True,
            "next_step": "STOP_FOR_HUMAN_REVIEW",
        }
    )
    hard["checks"][0]["status"] = "FAIL"
    validate_decision(hard, packet_sha)
    invalid = deepcopy(failed)
    invalid["action_items"] = invalid["action_items"][:2]
    try:
        validate_decision(invalid, packet_sha)
    except ValueError:
        pass
    else:
        raise AssertionError("two-action FAIL was not rejected")
    review = {
        "schema_version": RESULT_SCHEMA,
        "single_invocation": True,
        "resubmission_allowed": False,
        "packet": {"sha256": packet_sha},
        "decision": base,
    }
    assert evaluate_gate(review, None)["publication_authorized"] is True
    failed_review = deepcopy(review)
    failed_review["decision"] = failed
    pending = evaluate_gate(failed_review, None)
    assert pending["status"] == "blocked_pending_three_action_closure"
    closure = {
        "schema_version": CLOSURE_SCHEMA,
        "review_sha256": sha256_bytes(canonical_json(failed_review)),
        "no_resubmission_performed": True,
        "actions": [
            {
                "id": f"F{index}",
                "status": "RESOLVED",
                "implemented_change": "Corrected the synthetic record.",
                "evidence": ["self-test"],
            }
            for index in range(1, 4)
        ],
    }
    closed = evaluate_gate(failed_review, closure)
    assert closed["status"] == "approved_after_three_action_closure"
    assert closed["author_email_eligible_for_human_approval"] is True
    assert closed["author_email_dispatch_authorized"] is False
    email_sha = "b" * 64
    approval = {
        "schema_version": EMAIL_APPROVAL_SCHEMA,
        "decision": "APPROVE_SEND",
        "human_approved": True,
        "exact_draft_only": True,
        "approved_at_utc": "2026-08-01T00:00:00Z",
        "author_email_sha256": email_sha,
        "final_peer_review_sha256": sha256_bytes(canonical_json(failed_review)),
        "fable_action_closure_sha256": sha256_bytes(canonical_json(closure)),
    }
    validate_email_approval(approval, email_sha, failed_review, closure)
    hard_review = deepcopy(review)
    hard_review["decision"] = hard
    assert evaluate_gate(hard_review, None)["human_review_required"] is True
    supplemental = {
        "schema_version": SUPPLEMENTAL_CONSENSUS_SCHEMA,
        "source_fable_result_sha256": "c" * 64,
        "binding": {"packet_sha256": packet_sha},
        "policy": {
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
                "reviewer_family": family,
                "structured_valid": True,
                "validated_verdict": "PASS",
                "consensus_eligible": True,
            }
            for family in ("GLM", "Kimi")
        ],
        "decision": "PASS",
        "publication_authorized": True,
        "author_email_eligible_for_human_approval": True,
        "author_email_dispatch_authorized": False,
        "author_email_human_approval_required": True,
        "human_review_required": False,
    }
    supplemental_gate = evaluate_supplemental_consensus(
        supplemental,
        fable_result_sha256="c" * 64,
        packet_sha256=packet_sha,
    )
    assert supplemental_gate["publication_authorized"] is True
    assert supplemental_gate["author_email_dispatch_authorized"] is False
    failed_supplemental = deepcopy(supplemental)
    failed_supplemental["primary_pair"][1]["structured_valid"] = False
    failed_supplemental["primary_pair"][1]["validated_verdict"] = None
    failed_supplemental.update(
        {
            "decision": "HARD_FAIL",
            "publication_authorized": False,
            "author_email_eligible_for_human_approval": False,
            "human_review_required": True,
        }
    )
    failed_supplemental_gate = evaluate_supplemental_consensus(
        failed_supplemental,
        fable_result_sha256="c" * 64,
        packet_sha256=packet_sha,
    )
    assert failed_supplemental_gate["publication_authorized"] is False
    assert failed_supplemental_gate["human_review_required"] is True
    print("FABLE_FINAL_REVIEW_SELF_TEST_PASS")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build-packet")
    build.add_argument("--study-root", type=Path, default=Path.cwd())
    build.add_argument("--output", type=Path, required=True)
    review = subparsers.add_parser("review-once")
    review.add_argument("--study-root", type=Path, default=Path.cwd())
    review.add_argument("--packet", type=Path, required=True)
    review.add_argument("--output-root", type=Path, required=True)
    review.add_argument("--public-result", type=Path, required=True)
    review.add_argument("--markdown", type=Path, required=True)
    gate = subparsers.add_parser("check-gate")
    gate.add_argument("--study-root", type=Path, default=Path.cwd())
    subparsers.add_parser("self-test")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "build-packet":
        study_root = args.study_root.resolve()
        output = resolve_study_path(study_root, args.output)
        payload = build_packet(study_root)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        print(
            f"FABLE_REVIEW_PACKET output={output} sha256={sha256(output)}",
            flush=True,
        )
        return 0
    if args.command == "review-once":
        return run_review_once(args)
    if args.command == "check-gate":
        gate = gate_for_paths(args.study_root.resolve())
        print(json.dumps(gate, indent=2, sort_keys=True))
        return 0 if gate["publication_authorized"] else 5
    self_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
