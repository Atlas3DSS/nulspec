#!/usr/bin/env python3
"""Validate and summarize the citation-review/outer-teacher evidence."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import random
import statistics
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text)
    os.replace(temporary, path)


def distribution(values: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def numeric_summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "n": 0,
            "mean": None,
            "sample_sd": None,
            "median": None,
            "minimum": None,
            "maximum": None,
        }
    return {
        "n": len(values),
        "mean": round(statistics.mean(values), 6),
        "sample_sd": (round(statistics.stdev(values), 6) if len(values) > 1 else None),
        "median": round(statistics.median(values), 6),
        "minimum": min(values),
        "maximum": max(values),
    }


def percentile(sorted_values: list[float], probability: float) -> float:
    position = (len(sorted_values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def bootstrap_mean_interval(values: list[float], seed: int) -> list[float] | None:
    if not values:
        return None
    generator = random.Random(seed)
    estimates = sorted(
        statistics.mean(generator.choices(values, k=len(values))) for _ in range(10_000)
    )
    return [
        round(percentile(estimates, 0.025), 6),
        round(percentile(estimates, 0.975), 6),
    ]


def markdown_escape(value: Any) -> str:
    return " ".join(str(value).replace("|", "\\|").split())


def teacher_grades(
    manifest: dict[str, Any],
) -> tuple[
    dict[tuple[str, str], dict[str, Any]],
    set[str],
    set[tuple[str, str, str, str, str]],
]:
    grades: dict[tuple[str, str], dict[str, Any]] = {}
    batch_ids: set[str] = set()
    invocation_identities: set[tuple[str, str, str, str, str]] = set()
    for record in manifest["results"]:
        if not record.get("valid"):
            raise RuntimeError(f"invalid outer-teacher batch: {record['batch_id']}")
        trace = load(Path(record["teacher_trace_path"]))
        if record.get("teacher_trace_sha256") != sha256(
            Path(record["teacher_trace_path"])
        ):
            raise RuntimeError(
                f"outer-teacher trace hash mismatch: {record['batch_id']}"
            )
        if not trace.get("valid"):
            raise RuntimeError(f"invalid outer-teacher trace: {record['batch_id']}")
        stderr_lines = trace.get("invocation", {}).get("stderr", "").splitlines()

        def field(prefix: str) -> str:
            matches = [
                line[len(prefix) :] for line in stderr_lines if line.startswith(prefix)
            ]
            if len(matches) != 1:
                raise RuntimeError(
                    f"outer-teacher invocation lacks one {prefix!r} field: "
                    f"{record['batch_id']}"
                )
            return matches[0]

        if not stderr_lines or not stderr_lines[0].startswith("OpenAI Codex v"):
            raise RuntimeError(
                f"outer-teacher invocation lacks Codex version: {record['batch_id']}"
            )
        invocation_identities.add(
            (
                stderr_lines[0].removeprefix("OpenAI Codex v"),
                field("model: "),
                field("provider: "),
                field("reasoning effort: "),
                field("sandbox: "),
            )
        )
        batch_id = trace["batch_id"]
        batch_ids.add(batch_id)
        returned = []
        for grade in trace.get("grades") or []:
            audit_id = grade["audit_id"]
            key = (batch_id, audit_id)
            if key in grades:
                raise RuntimeError(f"duplicate teacher grade: {key}")
            grades[key] = grade
            returned.append(audit_id)
        if sorted(returned) != sorted(trace["audit_ids"]):
            raise RuntimeError(f"teacher audit-ID mismatch: {batch_id}")
    return grades, batch_ids, invocation_identities


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolved-manifest", type=Path, required=True)
    parser.add_argument("--qwen-run-manifest", type=Path, required=True)
    parser.add_argument("--teacher-run-manifest", type=Path, required=True)
    parser.add_argument("--cross-gpu", type=Path, required=True)
    parser.add_argument("--pre-recovery-teacher-manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    resolved = load(args.resolved_manifest)
    qwen = load(args.qwen_run_manifest)
    teacher = load(args.teacher_run_manifest)
    cross_gpu = load(args.cross_gpu)
    public_cross_gpu = dict(cross_gpu)
    public_cross_gpu.pop("run_manifest", None)
    target = resolved["target"]["arxiv_id"]
    if {
        qwen["target_arxiv_id"],
        cross_gpu["target_arxiv_id"],
    } != {target}:
        raise RuntimeError("citation manifests target different papers")

    audits = resolved["audits"]
    bibliography = {item["audit_id"]: item["bibliography"] for item in audits}
    evidence_levels = {
        item["audit_id"]: item["source_resolution"]["evidence"]["evidence_level"]
        for item in audits
    }
    if len(bibliography) != 47 or len(bibliography) != len(audits):
        raise RuntimeError("expected exactly 47 unique bibliography entries")

    grades, teacher_batch_ids, teacher_identities = teacher_grades(teacher)
    if len(teacher_identities) != 1:
        raise RuntimeError("outer-teacher invocation identity changed across batches")
    (
        teacher_cli_version,
        teacher_model,
        teacher_provider,
        teacher_reasoning_effort,
        teacher_sandbox,
    ) = next(iter(teacher_identities))
    qwen_batch_ids = {record["batch_id"] for record in qwen["results"]}
    if qwen_batch_ids != teacher_batch_ids:
        raise RuntimeError("Qwen and outer-teacher batch sets differ")
    if qwen.get("pending_count") != 0:
        raise RuntimeError("citation-review manifest still has pending batches")

    primary_by_audit: dict[str, dict[str, Any]] = {}
    duplicate_by_audit: dict[str, dict[str, Any]] = {}
    all_records: list[dict[str, Any]] = []
    for result in qwen["results"]:
        trace = load(Path(result["trace_path"]))
        if result.get("trace_sha256") != sha256(Path(result["trace_path"])):
            raise RuntimeError(f"Qwen trace hash mismatch: {result['batch_id']}")
        if trace["batch_id"] != result["batch_id"]:
            raise RuntimeError("Qwen trace batch-ID mismatch")
        review_by_id = {
            item["audit_id"]: item for item in trace.get("final_reviews") or []
        }
        kind = result.get("review_kind") or trace.get("review_kind")
        for audit_id in trace["audit_ids"]:
            if audit_id not in bibliography:
                raise RuntimeError(f"unknown audit ID in Qwen trace: {audit_id}")
            grade = grades.get((trace["batch_id"], audit_id))
            if grade is None:
                raise RuntimeError(
                    f"missing outer grade: {trace['batch_id']} {audit_id}"
                )
            record = {
                "audit_id": audit_id,
                "batch_id": trace["batch_id"],
                "review_kind": kind,
                "endpoint": trace["endpoint_label"],
                "qwen_trace_valid": bool(trace["valid"]),
                "evidence_validation_pass": bool(trace.get("evidence_validation_pass")),
                "qwen_review": review_by_id.get(audit_id),
                "teacher_grade": grade,
            }
            all_records.append(record)
            target_map = primary_by_audit if kind == "primary" else duplicate_by_audit
            if kind not in {"primary", "cross_gpu_duplicate"}:
                raise RuntimeError(f"unknown review kind: {kind}")
            if audit_id in target_map:
                raise RuntimeError(f"duplicate {kind} audit ID: {audit_id}")
            target_map[audit_id] = record

    if set(primary_by_audit) != set(bibliography):
        missing = sorted(set(bibliography) - set(primary_by_audit))
        raise RuntimeError(f"primary reviews do not cover bibliography: {missing}")
    if len(duplicate_by_audit) != 4:
        raise RuntimeError("expected four deterministic cross-GPU duplicates")

    primary = [primary_by_audit[key] for key in sorted(primary_by_audit)]
    primary_grades = [item["teacher_grade"] for item in primary]
    model_evaluable = [
        grade
        for grade in primary_grades
        if grade["failure_attribution"] in {"none", "model_review"}
    ]
    model_scores = [float(grade["overall_score_1_10"]) for grade in model_evaluable]
    critical_count = sum(bool(grade["critical_errors"]) for grade in model_evaluable)
    qwen_reviews = [item["qwen_review"] for item in primary if item["qwen_review"]]
    bootstrap_seed = int(
        hashlib.sha256(f"citation-score-bootstrap-v1|{target}".encode()).hexdigest()[
            :8
        ],
        16,
    )

    findings = []
    for item in primary:
        grade = item["teacher_grade"]
        if grade["teacher_verdict"] in {"supports", "non_claim"}:
            continue
        audit_id = item["audit_id"]
        findings.append(
            {
                "audit_id": audit_id,
                "title": bibliography[audit_id].get("title", ""),
                "evidence_level": evidence_levels[audit_id],
                "qwen_verdict": (
                    item["qwen_review"].get("verdict") if item["qwen_review"] else None
                ),
                "teacher_verdict": grade["teacher_verdict"],
                "teacher_score_1_10": grade["overall_score_1_10"],
                "failure_attribution": grade["failure_attribution"],
                "correction": grade["correction"],
            }
        )

    pre_recovery = []
    if args.pre_recovery_teacher_manifest:
        old = load(args.pre_recovery_teacher_manifest)
        old_grades, _, _ = teacher_grades(old)
        for (batch_id, audit_id), grade in sorted(old_grades.items()):
            pre_recovery.append(
                {
                    "batch_id": batch_id,
                    "audit_id": audit_id,
                    "score_1_10": grade["overall_score_1_10"],
                    "failure_attribution": grade["failure_attribution"],
                    "training_action": grade["training_action"],
                    "usable_for_training": grade["usable_for_training"],
                    "critical_errors": grade["critical_errors"],
                }
            )

    teacher_results = {item["batch_id"]: item for item in teacher["results"]}
    trace_inventory = []
    for item in sorted(qwen["results"], key=lambda value: value["batch_id"]):
        teacher_item = teacher_results[item["batch_id"]]
        trace_inventory.append(
            {
                "batch_id": item["batch_id"],
                "review_kind": item["review_kind"],
                "audit_ids": item["audit_ids"],
                "physical_route": item["endpoint"],
                "qwen_trace_sha256": item["trace_sha256"],
                "teacher_trace_sha256": teacher_item["teacher_trace_sha256"],
                "qwen_valid": item["valid"],
                "qwen_evidence_validation_pass": item["evidence_validation_pass"],
                "teacher_valid": teacher_item["valid"],
            }
        )

    result = {
        "schema_version": "nulspec-sprkd-citation-audit-summary-v2",
        "target_arxiv_id": target,
        "input_sha256": {
            "resolved_manifest": sha256(args.resolved_manifest),
            "qwen_run_manifest": sha256(args.qwen_run_manifest),
            "teacher_run_manifest": sha256(args.teacher_run_manifest),
            "cross_gpu": sha256(args.cross_gpu),
        },
        "coverage": {
            "unique_references": len(audits),
            "citation_context_blocks": resolved["counts"]["citation_context_blocks"],
            "resolution_status": resolved["resolution_summary"]["status_counts"],
            "evidence_levels": resolved["resolution_summary"]["evidence_level_counts"],
            "primary_reviews": len(primary),
            "cross_gpu_duplicates": len(duplicate_by_audit),
            "qwen_structurally_valid_primary": sum(
                item["qwen_trace_valid"] for item in primary
            ),
            "qwen_evidence_clean_primary": sum(
                item["evidence_validation_pass"] for item in primary
            ),
            "outer_teacher_primary_grades": len(primary_grades),
        },
        "qwen_primary_verdicts": distribution(
            [item["verdict"] for item in qwen_reviews]
        ),
        "teacher_primary_verdicts": distribution(
            [grade["teacher_verdict"] for grade in primary_grades]
        ),
        "failure_attribution": distribution(
            [grade["failure_attribution"] for grade in primary_grades]
        ),
        "model_quality": {
            "score_summary": numeric_summary(model_scores),
            "bootstrap_mean_95_interval": bootstrap_mean_interval(
                model_scores, bootstrap_seed
            ),
            "bootstrap_seed": bootstrap_seed,
            "bootstrap_resamples": 10_000,
            "critical_error_count": critical_count,
            "critical_error_types": distribution(
                [
                    error
                    for grade in model_evaluable
                    for error in grade["critical_errors"]
                ]
            ),
            "critical_error_rate": (
                round(critical_count / len(model_evaluable), 6)
                if model_evaluable
                else None
            ),
            "usable_for_training": sum(
                grade["usable_for_training"] for grade in primary_grades
            ),
            "training_actions": distribution(
                [grade["training_action"] for grade in primary_grades]
            ),
            "supervision_reduction_gate_passed": False,
        },
        "trace_provenance": {
            "qwen_protocol": qwen["protocol"],
            "outer_teacher_protocol": teacher["protocol"],
            "outer_teacher_identity": {
                "codex_cli_version": teacher_cli_version,
                "model": teacher_model,
                "provider": teacher_provider,
                "reasoning_effort": teacher_reasoning_effort,
                "sandbox": teacher_sandbox,
            },
            "model_aliases": qwen["models"],
            "model_sha256s": qwen["model_sha256s"],
            "outer_teacher_rubric_sha256": teacher["rubric_sha256"],
            "raw_traces_retained_locally": True,
            "raw_traces_published": False,
            "publication_note": (
                "The public package discloses immutable trace hashes without "
                "republishing retrieved source text."
            ),
            "inventory": trace_inventory,
        },
        "cross_gpu": public_cross_gpu,
        "non_supporting_or_unverifiable_findings": findings,
        "pre_recovery_negative_examples": pre_recovery,
    }

    output_json = args.output_dir / "citation_audit_results.json"
    atomic_write(output_json, json.dumps(result, indent=2, ensure_ascii=False) + "\n")

    score = result["model_quality"]["score_summary"]
    coverage = result["coverage"]
    lines = [
        "# Citation-use audit results",
        "",
        f"Target: arXiv:{target}. This audit is ancillary to the replication verdict.",
        "",
        "## Coverage",
        "",
        f"- {coverage['unique_references']} unique bibliography entries across "
        f"{coverage['citation_context_blocks']} citing-context blocks.",
        f"- Identity resolution: {result['coverage']['resolution_status']}.",
        f"- Evidence levels: {result['coverage']['evidence_levels']}.",
        f"- Qwen primary reviews: {coverage['primary_reviews']}; outer-teacher "
        f"grades: {coverage['outer_teacher_primary_grades']}; physical-GPU "
        f"duplicates: {coverage['cross_gpu_duplicates']}.",
        "",
        "## Reviewer quality",
        "",
        f"Model-evaluable score: mean {score['mean']} / 10, sample SD "
        f"{score['sample_sd']}, median {score['median']}, n={score['n']}; "
        f"bootstrap 95% mean interval "
        f"{result['model_quality']['bootstrap_mean_95_interval']}.",
        f"Critical errors: {result['model_quality']['critical_error_count']} "
        f"({result['model_quality']['critical_error_rate']}). The supervision "
        "reduction gate remains closed.",
        "All raw model and teacher traces are retained locally for supervised "
        "improvement. The public JSON publishes their SHA-256 inventory without "
        "republishing retrieved source text.",
        "",
        "## Findings requiring qualification or remaining unverifiable",
        "",
        "| Cited work | Evidence | Qwen | Teacher | Score | Correction |",
        "|---|---|---|---|---:|---|",
    ]
    for item in findings:
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_escape(item["title"]),
                    markdown_escape(item["evidence_level"]),
                    markdown_escape(item["qwen_verdict"] or "no valid review"),
                    markdown_escape(item["teacher_verdict"]),
                    str(item["teacher_score_1_10"]),
                    markdown_escape(item["correction"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "The table reports source-use support, not whether the citing paper's "
            "overall scientific conclusions are true. `Unverifiable` is not a "
            "finding of falsehood.",
        ]
    )
    output_markdown = args.output_dir / "CITATION_AUDIT_RESULTS.md"
    atomic_write(output_markdown, "\n".join(lines) + "\n")
    print(
        f"CITATION_AUDIT_ANALYSIS_COMPLETE references={len(primary)} "
        f"findings={len(findings)} output={output_json}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
