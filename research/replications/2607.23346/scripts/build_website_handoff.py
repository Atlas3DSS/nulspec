#!/usr/bin/env python3
"""Build the typed, fail-closed website handoff for the SPRKD study."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from fable_final_review import gate_for_paths


EXPECTED_SEEDS = list(range(5))
EXPECTED_RESULT_SCHEMAS = {
    "primary": "nulspec-sprkd-aggregate-v1",
    "extensions": "nulspec-sprkd-extension-aggregate-v1",
    "hessian": "nulspec-sprkd-hessian-aggregate-v1",
    "stability": "nulspec-sprkd-posthoc-stability-v1",
    "loss_contract": "nulspec-sprkd-loss-contract-aggregate-v1",
    "released_artifacts": "nulspec-sprkd-released-verification-v2",
    "citations": "nulspec-sprkd-citation-audit-summary-v2",
}
PAPER_REPORTED = {
    "sprkd": 94.80,
    "control_student": 94.47,
    "response_kd": 70.10,
    "control_teacher": 94.50,
    "weak_teacher": 70.13,
}
PRIMARY_MODELS = {
    "exact_public_sprkd": "sprkd_upstream_direct_init",
    "paper_intent_sprkd": "sprkd_paper_random_init",
    "control_student": "control_student",
    "exact_public_response_kd": "rkd_upstream_asr_teacher",
    "paper_intent_response_kd": "rkd_paper_weak_teacher",
    "control_teacher": "control_teacher",
    "weak_teacher": "weak_teacher_ensemble_mean",
}
EXTENSION_VOTES = [
    {
        "id": "author-intent",
        "label": "Clarify and rerun author intent",
        "role": "replication_strengthening",
    },
    {
        "id": "clean-room",
        "label": "Run an independent clean-room reproduction",
        "role": "reproducibility_strengthening",
    },
    {
        "id": "more-seeds",
        "label": "Measure stability across more seeds",
        "role": "robustness_replication",
    },
    {
        "id": "factorial",
        "label": "Isolate loss, initialization, and ASR choices",
        "role": "mechanistic_extension",
    },
    {
        "id": "curvature",
        "label": "Reconstruct the curvature analysis",
        "role": "replication_strengthening",
    },
    {
        "id": "modern-baselines",
        "label": "Compare modern KD baselines and datasets",
        "role": "new_extension",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--classification",
        required=True,
        choices=(
            "replicated",
            "partially_replicated",
            "not_replicated",
            "inconclusive",
        ),
    )
    parser.add_argument(
        "--underlying-claim-status",
        required=True,
        choices=("confirmed", "disconfirmed", "inconclusive"),
    )
    parser.add_argument("--rationale", required=True)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text())


def require_complete(payload: dict[str, Any], name: str) -> None:
    if payload.get("status") != "complete":
        raise ValueError(f"{name}: aggregate status is not complete")
    if payload.get("complete_seeds") != EXPECTED_SEEDS:
        raise ValueError(f"{name}: frozen seed set is incomplete or reordered")


def finite(value: Any, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label}: non-finite value")
    return result


def compact_summary(summary: dict[str, Any], label: str) -> dict[str, Any]:
    if int(summary.get("n", -1)) != 5:
        raise ValueError(f"{label}: expected five values")
    values = [finite(value, f"{label}.values") for value in summary["values"]]
    interval = [
        finite(value, f"{label}.t95_interval") for value in summary["t95_interval"]
    ]
    if len(values) != 5 or len(interval) != 2:
        raise ValueError(f"{label}: malformed summary")
    return {
        "n_training_seeds": 5,
        "per_seed": values,
        "mean": finite(summary["mean"], f"{label}.mean"),
        "sample_sd": finite(summary["sample_sd"], f"{label}.sample_sd"),
        "descriptive_t95_interval": interval,
        "unit": "percent_accuracy",
        "estimator": "final_sample_weighted_full_validation_accuracy",
    }


def comparison_for_seed(
    comparisons: dict[str, Any], seed: int
) -> dict[str, dict[str, Any]]:
    projected = {}
    for label, comparison in comparisons.items():
        values = comparison["accuracy_point_difference"]["values"]
        if len(values) != len(EXPECTED_SEEDS):
            raise ValueError(f"{label}: paired differences do not cover five seeds")
        tests = {int(row["seed"]): row for row in comparison["per_seed_mcnemar_exact"]}
        if sorted(tests) != EXPECTED_SEEDS:
            raise ValueError(f"{label}: McNemar rows do not cover five seeds")
        projected[label] = {
            "accuracy_point_difference": finite(
                values[EXPECTED_SEEDS.index(seed)], f"{label}.seed-{seed}"
            ),
            "unit": "percentage_points",
            "mcnemar_exact": tests[seed],
        }
    return projected


def sum_elapsed(rows: list[dict[str, Any]]) -> float:
    total = 0.0
    for run in rows:
        for model in run["models"].values():
            value = model.get("elapsed_seconds")
            if value is not None:
                total += finite(value, "elapsed_seconds")
    return total


def artifact(root: Path, relative: str, role: str) -> dict[str, Any]:
    path = root / relative
    if not path.is_file():
        raise FileNotFoundError(path)
    return {
        "path": relative,
        "role": role,
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def main() -> int:
    args = parse_args()
    root = args.study_root.resolve()
    result_paths = {
        "primary": "results/scratch_summary.json",
        "extensions": "results/extension_summary.json",
        "hessian": "results/hessian_extension_summary.json",
        "stability": "results/training_stability_summary.json",
        "loss_contract": "results/loss_contract_extension_summary.json",
        "released_artifacts": "results/released_artifact_verification.json",
        "citations": "results/citation_audit_results.json",
    }
    loaded = {name: load_json(root / path) for name, path in result_paths.items()}
    for name, schema in EXPECTED_RESULT_SCHEMAS.items():
        if loaded[name].get("schema_version") != schema:
            raise ValueError(f"{name}: unexpected result schema")
    for name in ("primary", "extensions", "hessian", "stability", "loss_contract"):
        require_complete(loaded[name], name)
    if loaded["citations"].get("target_arxiv_id") != "2607.23346v1":
        raise ValueError("citations: target arXiv record differs")

    primary = loaded["primary"]
    for seed, check in primary.get("integrity_checks", {}).items():
        if check.get("status") != "passed":
            raise ValueError(f"primary seed {seed}: integrity did not pass")
    if (
        sorted(int(seed) for seed in primary.get("integrity_checks", {}))
        != EXPECTED_SEEDS
    ):
        raise ValueError("primary: integrity coverage differs from the frozen seeds")

    primary_metrics = {}
    for public_name, model_name in PRIMARY_MODELS.items():
        row = primary["models"][model_name]
        primary_metrics[public_name] = {
            "model_key": model_name,
            "reported_accuracy": row.get("reported_accuracy"),
            "reported_accuracy_inside_descriptive_t95": row.get(
                "reported_accuracy_inside_t95"
            ),
            "observed": compact_summary(row["accuracy"], model_name),
        }

    run_rows = []
    for run in primary["runs"]:
        seed = int(run["seed"])
        if run.get("run_id") != f"seed-{seed}":
            raise ValueError(f"primary seed {seed}: unstable run id")
        environment = run.get("environment", {})
        if "hostname" in environment or "visible_devices" in environment.get("gpu", {}):
            raise ValueError(f"primary seed {seed}: private environment field remains")
        model_rows = {}
        for public_name, model_name in PRIMARY_MODELS.items():
            source = run["models"][model_name]
            model_rows[public_name] = {
                "model_key": model_name,
                **{
                    key: finite(source[key], f"seed-{seed}.{model_name}.{key}")
                    for key in (
                        "accuracy_sample_weighted",
                        "cross_entropy_sample_weighted",
                        "best_valid_accuracy_unweighted_batch_mean",
                        "final_valid_accuracy_unweighted_batch_mean",
                        "elapsed_seconds",
                        "parameter_count",
                    )
                    if key in source
                },
            }
        run_rows.append(
            {
                "run_id": run["run_id"],
                "seed": seed,
                "route": f"/studies/260723346/arms/seed-{seed}",
                "gpu": environment.get("gpu", {}).get("name", "unknown"),
                "environment": environment,
                "metrics": {
                    public_name: finite(
                        run["models"][model_name]["accuracy_sample_weighted"],
                        f"seed-{seed}.{model_name}",
                    )
                    for public_name, model_name in PRIMARY_MODELS.items()
                },
                "models": model_rows,
                "comparisons": comparison_for_seed(primary["comparisons"], seed),
                "integrity": run["integrity"],
            }
        )
    if [row["seed"] for row in run_rows] != EXPECTED_SEEDS:
        raise ValueError("primary: run rows differ from the ordered frozen seed set")

    extension = loaded["extensions"]
    hessian = loaded["hessian"]
    stability = loaded["stability"]
    loss_contract = loaded["loss_contract"]
    citation = loaded["citations"]
    final_review_gate = gate_for_paths(root)
    device_process_seconds = {
        "primary_training": finite(
            primary["operations"]["sum_recorded_training_stage_seconds_all_seeds"],
            "primary training seconds",
        ),
        "preregistered_extensions": sum_elapsed(extension["runs"]),
        "common_probe_hessian": sum_elapsed(hessian["runs"]),
        "posthoc_loss_contract": sum_elapsed(loss_contract["runs"]),
    }
    device_process_seconds["total"] = sum(device_process_seconds.values())

    artifact_specs = [
        ("README.md", "study_readme"),
        ("ONE_PAGE.md", "one_page_explainer"),
        ("REPORT.md", "full_report"),
        ("TESTS.md", "verification_log"),
        ("OPERATIONS.md", "execution_resource_log"),
        ("PROTOCOL.md", "frozen_primary_protocol"),
        ("EXTENSION_PROTOCOL.md", "frozen_extension_protocol"),
        ("POSTHOC_DIAGNOSTICS.md", "posthoc_register"),
        ("UPSTREAM_AUDIT.md", "upstream_issue_audit"),
        ("ERROR_LOG.md", "origin_separated_error_ledger"),
        ("SOURCE_MANIFEST.md", "source_manifest"),
        ("CITATION_AUDIT.md", "citation_audit_method"),
        ("CONTAINER.md", "container_instructions"),
        ("Dockerfile", "container_recipe"),
        ("requirements-replication.txt", "training_dependency_inputs"),
        ("requirements-replication.lock", "training_dependency_lock"),
        ("requirements-artifacts.txt", "artifact_dependency_inputs"),
        ("requirements-artifacts.lock", "artifact_replay_dependency_lock"),
        ("EXTENSION_ROADMAP.md", "extension_roadmap"),
        ("FRONTEND_HANDOFF.md", "typed_frontend_contract"),
        ("AUTHOR_QUESTIONS.md", "constructive_author_questions"),
        ("AUTHOR_EMAIL.md", "unsent_author_email_draft"),
        ("FABLE_REVIEW_PROTOCOL.md", "final_peer_review_protocol"),
        ("scripts/fable_final_review.py", "final_peer_review_gate"),
        ("results/executed_code_manifest.json", "executed_code_identity"),
        ("results/PRIMARY_ACCURACY_BY_SEED.png", "primary_figure"),
        ("results/SCRATCH_RESULTS.md", "primary_human_table"),
        ("results/scratch_summary.csv", "primary_machine_table"),
        ("results/EXTENSION_RESULTS.md", "extension_human_table"),
        ("results/extension_summary.csv", "extension_machine_table"),
        ("results/HESSIAN_EXTENSION_RESULTS.md", "hessian_human_table"),
        ("results/hessian_extension_summary.csv", "hessian_machine_table"),
        ("results/TRAINING_STABILITY_RESULTS.md", "stability_human_table"),
        ("results/LOSS_CONTRACT_EXTENSION_RESULTS.md", "loss_contract_human_table"),
        (
            "results/loss_contract_extension_summary.csv",
            "loss_contract_machine_table",
        ),
        ("results/CITATION_AUDIT_RESULTS.md", "citation_audit_human_table"),
        *[(path, f"machine_{name}") for name, path in result_paths.items()],
    ]
    final_review_path = root / "results/fable_final_peer_review.json"
    optional_review_artifacts = []
    if final_review_path.is_file():
        optional_review_artifacts.extend(
            [
                (
                    "results/fable_final_review_packet.json",
                    "final_peer_review_packet",
                ),
                (
                    "results/fable_final_peer_review.json",
                    "final_peer_review_result",
                ),
                ("FABLE_FINAL_REVIEW.md", "final_peer_review_human_record"),
            ]
        )
    optional_review_artifacts.extend(
        [
            (
                "results/fable_action_closure.json",
                "final_peer_review_action_closure",
            ),
            (
                "results/author_email_human_approval.json",
                "author_email_human_approval",
            ),
        ]
    )
    artifact_specs.extend(
        (path, role)
        for path, role in optional_review_artifacts
        if (root / path).is_file()
    )
    artifacts = [artifact(root, path, role) for path, role in artifact_specs]

    payload = {
        "schema_version": "nulspec-classification-accuracy-study-handoff-v1",
        "study": {
            "id": "260723346",
            "slug": "sprkd-malaria",
            "title": "SPRKD: Effective Knowledge Distillation for Deep Neural Networks via Saddle Region Approximation",
            "arxiv_id": "2607.23346v1",
            "arxiv_url": "https://arxiv.org/abs/2607.23346v1",
            "upstream_commit": "7f1655ff1295c9a6dcf8d24f6410a036cd7e3497",
            "scope": "Experiment 1 malaria classification",
        },
        "classification": {
            "replication_outcome": args.classification,
            "underlying_method_claim": args.underlying_claim_status,
            "rationale": args.rationale,
            "decision_source": "PROTOCOL.md",
        },
        "metrics_schema": {
            "id": "sprkd_trial_accuracy_v1",
            "primary_unit": "percent_accuracy",
            "primary_estimator": "final_sample_weighted_full_validation_accuracy",
            "uncertainty": "descriptive Student t interval across five independent training seeds",
            "not_prompt_bootstrap": True,
            "not_equivalence_test": True,
        },
        "paper_reported_accuracy": PAPER_REPORTED,
        "primary": {
            "metrics": primary_metrics,
            "comparisons": primary["comparisons"],
            "runs": run_rows,
        },
        "diagnostics": {
            "preregistered_extensions": {
                "scope": "E1 conventional-logit KD and E2 lowest-loss ASR",
                "models": extension["models"],
                "comparisons": extension["comparisons"],
                "runs": extension["runs"],
            },
            "common_probe_hessian": {
                "scope": hessian["interpretation_scope"],
                "models": hessian["models"],
                "ordering": hessian["ordering"],
                "paired_trace_differences": hessian["paired_trace_differences"],
                "runs": hessian["runs"],
            },
            "posthoc_stability": {
                "scope": stability["interpretation_scope"],
                "aggregates": stability["aggregates"],
                "seeds": stability["seeds"],
            },
            "posthoc_loss_contract": {
                "scope": loss_contract["interpretation_scope"],
                "models": loss_contract["models"],
                "comparisons": loss_contract["comparisons"],
                "runs": loss_contract["runs"],
            },
        },
        "citation_audit": {
            "verdict_bearing": False,
            "coverage": citation["coverage"],
            "outer_teacher_verdicts": citation["teacher_primary_verdicts"],
            "local_reviewer_quality": citation["model_quality"],
            "trace_provenance": citation["trace_provenance"],
        },
        "final_peer_review": {
            "protocol": "nulspec-fable-one-shot-final-gate-v1",
            "protocol_document": "FABLE_REVIEW_PROTOCOL.md",
            "reviewer": "Fable",
            "single_invocation": True,
            "resubmission_allowed": False,
            **final_review_gate,
        },
        "compute": {
            "recorded_device_process_seconds": device_process_seconds,
            "recorded_device_process_hours_total": device_process_seconds["total"]
            / 3600.0,
            "accounting_note": (
                "Sum of runner-reported stage wall times. Concurrent processes on "
                "one physical GPU are counted separately; this is compute-process "
                "accounting, not elapsed wall time or measured GPU-active time."
            ),
        },
        "artifacts": artifacts,
        "routes": {
            "study": "/studies/260723346",
            "arms": [row["route"] for row in run_rows],
        },
        "extension_vote": {
            "button_label": "Vote to extend this paper",
            "question": "Which follow-up would most improve confidence in this result?",
            "choices": EXTENSION_VOTES,
            "effect": "Schedules new evidence and never rewrites the frozen result.",
        },
        "publication_status": {
            "canonical_site_import": "blocked_pending_typed_accuracy_frontend",
            "reason": (
                "The current site validator accepts reward-delta arms, not "
                "classification-accuracy trials. Accuracy is not relabeled as reward."
            ),
            "frontend_contract": "FRONTEND_HANDOFF.md",
            "research_release_gate": final_review_gate,
            "author_email_dispatch": (
                "authorized"
                if final_review_gate["author_email_dispatch_authorized"]
                else final_review_gate["author_email_approval_status"]
            ),
        },
    }

    output = args.output
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(
        f"WEBSITE_HANDOFF classification={args.classification} "
        f"seeds={len(run_rows)} output={output}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
