#!/usr/bin/env python3
"""Validate and compare traced evaluations for arXiv:2607.17674."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Sequence

import numpy as np


SCHEMA_VERSION = 1
ANALYSIS_VERSION = "1.0.0"
EXPECTED_INSTRUMENTATION_VERSION = "1.0.1"
FIDELITY_SUCCESS_OUTCOMES = {"unique_strategy", "ambiguous_strategy"}
ANALOGICAL_DECISIONS = (
    "released_overlap",
    "nonempty_set_equality",
    "unique_only",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                raise ValueError(f"blank JSONL row at {path}:{line_number}")
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"non-object JSONL row at {path}:{line_number}")
            rows.append(payload)
    return rows


def require_probability(value: Any, *, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    numeric = float(value)
    if not math.isfinite(numeric) or not 0.0 <= numeric <= 1.0:
        raise ValueError(f"{label} must be finite and inside [0, 1]")
    return numeric


def fidelity_summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("fidelity trace is empty")
    counts = Counter(str(row.get("outcome")) for row in rows)
    successes = sum(counts[name] for name in FIDELITY_SUCCESS_OUTCOMES)
    return {
        "distributional_fidelity": successes / len(rows),
        "num_examples": len(rows),
        "outcome_counts": dict(sorted(counts.items())),
    }


def analogical_summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("analogical trace is empty")
    for index, row in enumerate(rows):
        source = {str(item) for item in row.get("source_strategies", [])}
        target = {str(item) for item in row.get("target_strategies", [])}
        nonempty = bool(source) and bool(target)
        expected = {
            "released_overlap": bool(source & target),
            "nonempty_set_equality": bool(nonempty and source == target),
            "unique_only": bool(
                len(source) == 1 and len(target) == 1 and source == target
            ),
        }
        if row.get("decisions") != expected:
            raise ValueError(f"analogical decision mismatch at row {index}")
    decision_counts: dict[str, int] = {}
    for name in ANALOGICAL_DECISIONS:
        decision_counts[name] = sum(
            bool(row.get("decisions", {}).get(name)) for row in rows
        )
    total = len(rows)
    released = decision_counts["released_overlap"] / total
    return {
        "analogical_consistency": released,
        "analogical_consistency_released_overlap": released,
        "analogical_consistency_nonempty_set_equality": (
            decision_counts["nonempty_set_equality"] / total
        ),
        "analogical_consistency_unique_only": (decision_counts["unique_only"] / total),
        "num_pairs": total,
        "ambiguous_pair_rate": sum(
            len(row.get("source_strategies", [])) > 1
            or len(row.get("target_strategies", [])) > 1
            for row in rows
        )
        / total,
        "undefined_strategy_pair_rate": sum(
            not row.get("source_strategies") or not row.get("target_strategies")
            for row in rows
        )
        / total,
    }


def require_close(observed: Any, expected: Any, *, label: str) -> None:
    if isinstance(expected, dict):
        if observed != expected:
            raise ValueError(f"{label} does not match recomputed trace counts")
        return
    if isinstance(expected, int) and not isinstance(expected, bool):
        if observed != expected:
            raise ValueError(
                f"{label} is {observed!r}, recomputed count is {expected!r}"
            )
        return
    observed_numeric = require_probability(observed, label=label)
    expected_numeric = require_probability(expected, label=f"recomputed {label}")
    if not math.isclose(observed_numeric, expected_numeric, abs_tol=1e-15):
        raise ValueError(
            f"{label} is {observed_numeric}, recomputed value is {expected_numeric}"
        )


def validate_trace_dir(path: Path, *, expected_mode: str) -> dict[str, Any]:
    path = path.expanduser().resolve()
    required = (
        "run.start.json",
        "fidelity.jsonl",
        "analogical.jsonl",
        "metrics.json",
        "run.complete.json",
    )
    missing = [name for name in required if not (path / name).is_file()]
    if missing:
        raise ValueError(
            f"trace directory is incomplete ({', '.join(missing)}): {path}"
        )

    start = load_json(path / "run.start.json")
    complete = load_json(path / "run.complete.json")
    metrics = load_json(path / "metrics.json")
    if start.get("rng_mode") != expected_mode:
        raise ValueError(
            f"trace RNG mode is {start.get('rng_mode')!r}, expected {expected_mode!r}"
        )
    if start.get("instrumentation_version") != EXPECTED_INSTRUMENTATION_VERSION:
        raise ValueError(
            "trace instrumentation version is not the registered analyzer input"
        )
    if start.get("workspace_tracked_clean") is not True:
        raise ValueError("trace workspace was not tracked-clean")
    if start.get("upstream_tracked_clean") is not True:
        raise ValueError("trace upstream tree was not tracked-clean")
    if complete.get("status") != "complete":
        raise ValueError("trace completion status is not complete")
    for key, value in start.items():
        if complete.get(key) != value:
            raise ValueError(f"completion manifest changed start field {key}")

    hashes = complete.get("artifact_sha256")
    if not isinstance(hashes, dict):
        raise ValueError("completion manifest lacks artifact hashes")
    for name in required[:-1]:
        expected_hash = hashes.get(name)
        actual_hash = sha256_file(path / name)
        if expected_hash != actual_hash:
            raise ValueError(f"artifact hash mismatch for {name}")

    fidelity_rows = load_jsonl(path / "fidelity.jsonl")
    analogical_rows = load_jsonl(path / "analogical.jsonl")
    expected_examples = int(metrics.get("num_examples", -1))
    expected_pairs = int(start.get("num_pairs", -1))
    if len(fidelity_rows) != expected_examples:
        raise ValueError("fidelity row count does not match metrics")
    if len(analogical_rows) != expected_pairs:
        raise ValueError("analogical row count does not match start manifest")
    if [row.get("index") for row in fidelity_rows] != list(range(len(fidelity_rows))):
        raise ValueError("fidelity indices are not exact and consecutive")
    if [row.get("pair_index") for row in analogical_rows] != list(
        range(len(analogical_rows))
    ):
        raise ValueError("analogical pair indices are not exact and consecutive")

    recomputed = {
        **fidelity_summary(fidelity_rows),
        **analogical_summary(analogical_rows),
    }
    for key, expected in recomputed.items():
        require_close(metrics.get(key), expected, label=key)
    if metrics.get("rng_mode") != expected_mode:
        raise ValueError("metrics RNG mode does not match its trace")

    return {
        "path": path,
        "start": start,
        "complete": complete,
        "metrics": metrics,
        "fidelity_rows": fidelity_rows,
        "analogical_rows": analogical_rows,
        "completion_manifest_sha256": sha256_file(path / "run.complete.json"),
    }


def task_summaries(trace: dict[str, Any]) -> dict[str, Any]:
    fidelity_by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    analogical_by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in trace["fidelity_rows"]:
        fidelity_by_task[str(row["task_name"])].append(row)
    for row in trace["analogical_rows"]:
        analogical_by_task[str(row["task_name"])].append(row)
    tasks = sorted(set(fidelity_by_task) | set(analogical_by_task))
    result: dict[str, Any] = {}
    for task in tasks:
        result[task] = {}
        if fidelity_by_task[task]:
            result[task]["fidelity"] = fidelity_summary(fidelity_by_task[task])
        if analogical_by_task[task]:
            result[task]["analogical"] = analogical_summary(analogical_by_task[task])
    return result


def derived_seed(base_seed: int, label: str) -> int:
    digest = hashlib.sha256(f"{base_seed}:{label}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def binary_bootstrap_ci(
    values: Sequence[bool],
    *,
    repetitions: int,
    seed: int,
    label: str,
) -> dict[str, Any]:
    if not values:
        raise ValueError(f"cannot bootstrap empty values for {label}")
    count = sum(bool(value) for value in values)
    total = len(values)
    estimate = count / total
    rng = np.random.default_rng(derived_seed(seed, label))
    draws = rng.binomial(total, estimate, size=repetitions) / total
    lower, upper = np.quantile(draws, [0.025, 0.975], method="linear")
    return {
        "estimate": estimate,
        "lower_95": float(lower),
        "upper_95": float(upper),
        "n": total,
        "bootstrap_repetitions": repetitions,
        "method": "nonparametric row bootstrap; binary-count equivalent",
    }


def paired_difference_bootstrap_ci(
    released: Sequence[bool],
    advancing: Sequence[bool],
    *,
    repetitions: int,
    seed: int,
    label: str,
) -> dict[str, Any]:
    if len(released) != len(advancing) or not released:
        raise ValueError(f"paired values are missing or misaligned for {label}")
    differences = [int(new) - int(old) for old, new in zip(released, advancing)]
    counts = Counter(differences)
    support = np.asarray([-1.0, 0.0, 1.0])
    probabilities = np.asarray([counts[-1], counts[0], counts[1]], dtype=float)
    probabilities /= probabilities.sum()
    rng = np.random.default_rng(derived_seed(seed, label))
    sampled_counts = rng.multinomial(
        len(differences),
        probabilities,
        size=repetitions,
    )
    draws = sampled_counts @ support / len(differences)
    lower, upper = np.quantile(draws, [0.025, 0.975], method="linear")
    return {
        "estimate_advancing_minus_released": sum(differences) / len(differences),
        "lower_95": float(lower),
        "upper_95": float(upper),
        "n": len(differences),
        "difference_counts": {str(key): counts[key] for key in (-1, 0, 1)},
        "bootstrap_repetitions": repetitions,
        "method": "paired nonparametric row bootstrap",
    }


def fidelity_values(trace: dict[str, Any]) -> list[bool]:
    return [
        str(row["outcome"]) in FIDELITY_SUCCESS_OUTCOMES
        for row in trace["fidelity_rows"]
    ]


def analogical_values(trace: dict[str, Any], decision: str) -> list[bool]:
    return [bool(row["decisions"][decision]) for row in trace["analogical_rows"]]


def validate_cross_trace_identity(
    released: dict[str, Any], advancing: dict[str, Any]
) -> None:
    invariant_fields = (
        "instrumentation_version",
        "checkpoint_sha256",
        "factorization_config_sha256",
        "workspace_revision",
        "upstream_revision",
        "environment",
        "device",
        "seed",
        "batch_size",
        "num_pairs",
    )
    for key in invariant_fields:
        if released["start"].get(key) != advancing["start"].get(key):
            raise ValueError(f"trace comparison changes invariant field {key}")
    released_examples = [
        (row.get("index"), row.get("example_id"), row.get("task_name"))
        for row in released["fidelity_rows"]
    ]
    advancing_examples = [
        (row.get("index"), row.get("example_id"), row.get("task_name"))
        for row in advancing["fidelity_rows"]
    ]
    if released_examples != advancing_examples:
        raise ValueError("fidelity traces are not prompt-aligned")
    released_pairs = [
        (
            row.get("pair_index"),
            row.get("source_example_id"),
            row.get("target_example_id"),
            row.get("task_name"),
        )
        for row in released["analogical_rows"]
    ]
    advancing_pairs = [
        (
            row.get("pair_index"),
            row.get("source_example_id"),
            row.get("target_example_id"),
            row.get("task_name"),
        )
        for row in advancing["analogical_rows"]
    ]
    if released_pairs != advancing_pairs:
        raise ValueError("analogical traces are not pair-aligned")


def primary_parity(
    primary_metrics_path: Path, released: dict[str, Any]
) -> dict[str, Any]:
    primary = load_json(primary_metrics_path)
    comparisons = {
        "distributional_fidelity": (
            float(primary["distributional_fidelity"])
            == float(released["metrics"]["distributional_fidelity"])
        ),
        "analogical_consistency": (
            float(primary["analogical_consistency"])
            == float(released["metrics"]["analogical_consistency"])
        ),
    }
    if not all(comparisons.values()):
        raise ValueError(
            "released-reseed trace does not exactly reproduce primary metrics"
        )
    return {
        "exact_match": True,
        "by_metric": comparisons,
        "primary_metrics_sha256": sha256_file(primary_metrics_path),
    }


def build_analysis(
    *,
    primary_metrics_path: Path,
    released_dir: Path,
    advancing_dir: Path,
    repetitions: int,
    bootstrap_seed: int,
) -> dict[str, Any]:
    if repetitions < 1:
        raise ValueError("bootstrap repetitions must be positive")
    released = validate_trace_dir(released_dir, expected_mode="released-reseed")
    advancing = validate_trace_dir(advancing_dir, expected_mode="advancing")
    validate_cross_trace_identity(released, advancing)
    parity = primary_parity(primary_metrics_path, released)

    advancing_intervals = {
        "distributional_fidelity": binary_bootstrap_ci(
            fidelity_values(advancing),
            repetitions=repetitions,
            seed=bootstrap_seed,
            label="advancing-fidelity",
        )
    }
    for decision in ANALOGICAL_DECISIONS:
        advancing_intervals[f"analogical_{decision}"] = binary_bootstrap_ci(
            analogical_values(advancing, decision),
            repetitions=repetitions,
            seed=bootstrap_seed,
            label=f"advancing-analogical-{decision}",
        )

    paired_differences = {
        "distributional_fidelity": paired_difference_bootstrap_ci(
            fidelity_values(released),
            fidelity_values(advancing),
            repetitions=repetitions,
            seed=bootstrap_seed,
            label="difference-fidelity",
        )
    }
    for decision in ANALOGICAL_DECISIONS:
        paired_differences[f"analogical_{decision}"] = paired_difference_bootstrap_ci(
            analogical_values(released, decision),
            analogical_values(advancing, decision),
            repetitions=repetitions,
            seed=bootstrap_seed,
            label=f"difference-analogical-{decision}",
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "analysis_version": ANALYSIS_VERSION,
        "paper_id": "2607.17674",
        "primary_parity": parity,
        "released_reseed": {
            "metrics": released["metrics"],
            "tasks": task_summaries(released),
            "completion_manifest_sha256": released["completion_manifest_sha256"],
            "uncertainty": {"status": "not_computed_due_to_batchwise_rng_dependence"},
        },
        "advancing": {
            "metrics": advancing["metrics"],
            "tasks": task_summaries(advancing),
            "completion_manifest_sha256": advancing["completion_manifest_sha256"],
            "conditional_95_intervals": advancing_intervals,
        },
        "paired_advancing_minus_released": paired_differences,
        "uncertainty_scope": (
            "Prompt/pair resampling conditional on one trained checkpoint and "
            "one generation per prompt; excludes fresh-training and repeated-"
            "decoding variability."
        ),
        "bootstrap": {
            "repetitions": repetitions,
            "seed": bootstrap_seed,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    released = payload["released_reseed"]["metrics"]
    advancing = payload["advancing"]["metrics"]
    lines = [
        "# Instrumented evaluation sensitivity",
        "",
        "Primary parity: exact pass.",
        "",
        "| Metric | Released reseed | Advancing stream | Difference |",
        "| --- | ---: | ---: | ---: |",
    ]
    mappings = (
        ("Distributional Fidelity", "distributional_fidelity"),
        ("Analogical Consistency", "analogical_consistency"),
        (
            "Analogical exact-set equality",
            "analogical_consistency_nonempty_set_equality",
        ),
        ("Analogical unique-only", "analogical_consistency_unique_only"),
    )
    difference_keys = {
        "distributional_fidelity": "distributional_fidelity",
        "analogical_consistency": "analogical_released_overlap",
        "analogical_consistency_nonempty_set_equality": (
            "analogical_nonempty_set_equality"
        ),
        "analogical_consistency_unique_only": "analogical_unique_only",
    }
    for label, key in mappings:
        difference = payload["paired_advancing_minus_released"][difference_keys[key]][
            "estimate_advancing_minus_released"
        ]
        lines.append(
            f"| {label} | {released[key]:.4f} | {advancing[key]:.4f} | "
            f"{difference:+.4f} |"
        )
    lines.extend(
        [
            "",
            "Intervals in the JSON are conditional prompt/pair-resampling "
            "intervals for the advancing-stream sensitivity. They do not "
            "estimate fresh-training or repeated-decoding variability.",
            "",
        ]
    )
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-metrics", type=Path, required=True)
    parser.add_argument("--released-dir", type=Path, required=True)
    parser.add_argument("--advancing-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--bootstrap-repetitions", type=int, default=10_000)
    parser.add_argument("--bootstrap-seed", type=int, default=260717674)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    output = args.output.expanduser().resolve()
    markdown = args.markdown.expanduser().resolve()
    for path in (output, markdown):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite analysis output: {path}")
    payload = build_analysis(
        primary_metrics_path=args.primary_metrics.expanduser().resolve(),
        released_dir=args.released_dir,
        advancing_dir=args.advancing_dir,
        repetitions=args.bootstrap_repetitions,
        bootstrap_seed=args.bootstrap_seed,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown.write_text(render_markdown(payload), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
