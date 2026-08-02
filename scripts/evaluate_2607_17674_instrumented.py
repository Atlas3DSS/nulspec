#!/usr/bin/env python3
"""Record every outcome behind the two arXiv:2607.17674 evaluation metrics."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, is_dataclass, replace
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from typing import Any, Iterable, Literal


WORKSPACE = Path(__file__).resolve().parents[1]
DEFAULT_UPSTREAM = (
    WORKSPACE / "research" / "replications" / "2607.17674" / "work" / "upstream"
)
SCHEMA_VERSION = 1
INSTRUMENTATION_VERSION = "1.0.1"
RngMode = Literal["released-reseed", "advancing"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def generation_seed(
    mode: RngMode,
    *,
    base_seed: int,
    batch_start: int,
    phase: Literal["fidelity", "analogical"],
) -> int | None:
    """Return the exact per-call seed for a registered RNG mode."""

    if mode == "advancing":
        return None
    if mode != "released-reseed":
        raise ValueError(f"unsupported RNG mode: {mode}")
    if phase == "fidelity":
        return int(base_seed)
    return int(base_seed) + int(batch_start) + 1


def fidelity_metrics(outcomes: Iterable[str]) -> dict[str, Any]:
    counts = Counter(str(outcome) for outcome in outcomes)
    total = sum(counts.values())
    if total < 1:
        raise ValueError("at least one fidelity outcome is required")
    compatible = counts["unique_strategy"] + counts["ambiguous_strategy"]
    return {
        "distributional_fidelity": compatible / total,
        "num_examples": total,
        "outcome_counts": dict(sorted(counts.items())),
    }


def analogical_decisions(
    source_strategies: set[str], target_strategies: set[str]
) -> dict[str, bool]:
    """Evaluate released and sensitivity conventions for one generated pair."""

    nonempty = bool(source_strategies) and bool(target_strategies)
    return {
        "released_overlap": bool(source_strategies & target_strategies),
        "nonempty_set_equality": bool(
            nonempty and source_strategies == target_strategies
        ),
        "unique_only": bool(
            len(source_strategies) == 1
            and len(target_strategies) == 1
            and source_strategies == target_strategies
        ),
    }


def analogical_metrics(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    materialized = list(rows)
    if not materialized:
        raise ValueError("at least one analogical outcome is required")
    total = len(materialized)
    decision_names = (
        "released_overlap",
        "nonempty_set_equality",
        "unique_only",
    )
    sums = {
        name: sum(bool(row["decisions"][name]) for row in materialized)
        for name in decision_names
    }
    return {
        "analogical_consistency": sums["released_overlap"] / total,
        "analogical_consistency_released_overlap": (sums["released_overlap"] / total),
        "analogical_consistency_nonempty_set_equality": (
            sums["nonempty_set_equality"] / total
        ),
        "analogical_consistency_unique_only": sums["unique_only"] / total,
        "num_pairs": total,
        "ambiguous_pair_rate": sum(
            len(row["source_strategies"]) > 1 or len(row["target_strategies"]) > 1
            for row in materialized
        )
        / total,
        "undefined_strategy_pair_rate": sum(
            not row["source_strategies"] or not row["target_strategies"]
            for row in materialized
        )
        / total,
    }


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def require_new_output_dir(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"refusing existing instrumentation output: {path}")
    path.mkdir(parents=True)


def load_upstream(upstream: Path) -> SimpleNamespace:
    upstream = upstream.expanduser().resolve()
    if not (upstream / "experiments" / "factorization" / "evaluate.py").is_file():
        raise FileNotFoundError(f"pinned upstream tree is incomplete: {upstream}")
    if str(upstream) not in sys.path:
        sys.path.insert(0, str(upstream))

    from core.analysis.strategy_attribution import classify_generation_outcome
    from core.train.collate import left_pad_batch, right_pad_batch
    from core.train.seed import set_global_seed
    from experiments.factorization.eval_utils import (
        _generate_continuous_latent_sequences,
        build_continuous_generation_prompt,
    )
    from experiments.factorization.evaluate import (
        _load_run_config,
        _resolve_checkpoint,
        _resolve_device,
        _sampling_config,
        load_evaluation_bundle,
        sample_analogical_pairs,
    )
    from experiments.factorization.precision import bfloat16_context
    from experiments.factorization.train_utils import build_router_prompt

    return SimpleNamespace(
        classify_generation_outcome=classify_generation_outcome,
        left_pad_batch=left_pad_batch,
        right_pad_batch=right_pad_batch,
        set_global_seed=set_global_seed,
        generate_continuous_latent_sequences=_generate_continuous_latent_sequences,
        build_continuous_generation_prompt=build_continuous_generation_prompt,
        load_run_config=_load_run_config,
        resolve_checkpoint=_resolve_checkpoint,
        resolve_device=_resolve_device,
        sampling_config=_sampling_config,
        load_evaluation_bundle=load_evaluation_bundle,
        sample_analogical_pairs=sample_analogical_pairs,
        bfloat16_context=bfloat16_context,
        build_router_prompt=build_router_prompt,
    )


def effective_task_name(task: Any, record: Any) -> str:
    if str(task.metadata.task_name) == "multi_task":
        return str(task.task_name_for_input(record.x))
    return str(task.metadata.task_name)


def strategy_set(task: Any, record: Any, y_text: str | None) -> set[str]:
    if y_text is None:
        return set()
    validation = task.validate_y_text(record.x, y_text)
    if not validation.parse_success or validation.strategy_matches is None:
        return set()
    return {str(strategy) for strategy in validation.strategy_matches}


def evaluate_fidelity_traced(
    *,
    deps: SimpleNamespace,
    bundle: Any,
    records: tuple[Any, ...],
    batch_size: int,
    sampling: Any,
    seed: int,
    rng_mode: RngMode,
    output_path: Path,
) -> dict[str, Any]:
    task = bundle.responses.task
    tokenizer = bundle.tokenizer_runtime
    model = bundle.factorization_model
    outcomes: list[str] = []

    deps.set_global_seed(seed)
    with deps.bfloat16_context(
        enabled=bool(bundle.config.get("use_bfloat16", False)),
        device=bundle.device,
    ):
        import torch

        with torch.no_grad():
            for start in range(0, len(records), batch_size):
                chunk = records[start : start + batch_size]
                router_batch = deps.right_pad_batch(
                    [
                        deps.build_router_prompt(
                            record,
                            z_open_id=tokenizer.z_open_id,
                        )
                        for record in chunk
                    ],
                    pad_id=tokenizer.pad_id,
                )
                router_output = model.route(
                    input_ids=router_batch.input_ids.to(bundle.device),
                    attention_mask=router_batch.attention_mask.to(bundle.device),
                )
                prompts = [
                    deps.build_continuous_generation_prompt(
                        record=record,
                        z_open_id=tokenizer.z_open_id,
                        z_empty_id=tokenizer.z_empty_id,
                        z_close_id=tokenizer.z_close_id,
                    )
                    for record in chunk
                ]
                prompt_batch = deps.left_pad_batch(prompts, pad_id=tokenizer.pad_id)
                generated = (
                    deps.generate_continuous_latent_sequences(
                        factorization_model=model,
                        input_ids=prompt_batch.input_ids.to(bundle.device),
                        attention_mask=prompt_batch.attention_mask.to(bundle.device),
                        z_vectors=router_output.router_z.to(bundle.device),
                        sampling_cfg=replace(
                            sampling,
                            seed=generation_seed(
                                rng_mode,
                                base_seed=seed,
                                batch_start=start,
                                phase="fidelity",
                            ),
                        ),
                    )
                    .detach()
                    .cpu()
                    .tolist()
                )

                for offset, (record, sequence) in enumerate(
                    zip(chunk, generated, strict=True)
                ):
                    y_text = tokenizer.extract_y_text(sequence)
                    validation = (
                        task.validate_y_text(record.x, y_text)
                        if y_text is not None
                        else None
                    )
                    outcome = (
                        str(deps.classify_generation_outcome(validation))
                        if validation is not None
                        else "parse_failure"
                    )
                    strategies = (
                        sorted(str(item) for item in validation.strategy_matches)
                        if validation is not None
                        and validation.parse_success
                        and validation.strategy_matches is not None
                        else []
                    )
                    outcomes.append(outcome)
                    append_jsonl(
                        output_path,
                        {
                            "schema_version": SCHEMA_VERSION,
                            "index": start + offset,
                            "example_id": int(record.example_id),
                            "task_name": effective_task_name(task, record),
                            "x": jsonable(record.x),
                            "y_text": y_text,
                            "outcome": outcome,
                            "strategies": strategies,
                        },
                    )
    return fidelity_metrics(outcomes)


def evaluate_analogical_traced(
    *,
    deps: SimpleNamespace,
    bundle: Any,
    records: tuple[Any, ...],
    num_pairs: int,
    batch_size: int,
    sampling: Any,
    seed: int,
    rng_mode: RngMode,
    output_path: Path,
) -> dict[str, Any]:
    import torch

    task = bundle.responses.task
    tokenizer = bundle.tokenizer_runtime
    model = bundle.factorization_model
    pairs = deps.sample_analogical_pairs(
        records,
        task=task,
        num_pairs=num_pairs,
        seed=seed,
    )
    metric_rows: list[dict[str, Any]] = []

    deps.set_global_seed(seed)
    with torch.no_grad():
        for start in range(0, len(pairs), batch_size):
            chunk = pairs[start : start + batch_size]
            router_batch = deps.right_pad_batch(
                [
                    deps.build_router_prompt(
                        pair.source,
                        z_open_id=tokenizer.z_open_id,
                    )
                    for pair in chunk
                ],
                pad_id=tokenizer.pad_id,
            )
            with deps.bfloat16_context(
                enabled=bool(bundle.config.get("use_bfloat16", False)),
                device=bundle.device,
            ):
                router_output = model.route(
                    input_ids=router_batch.input_ids.to(bundle.device),
                    attention_mask=router_batch.attention_mask.to(bundle.device),
                )

            prompts: list[dict[str, tuple[int, ...]]] = []
            latent_rows: list[Any] = []
            for pair, latent in zip(chunk, router_output.router_z, strict=True):
                for record in (pair.source, pair.target):
                    prompts.append(
                        deps.build_continuous_generation_prompt(
                            record=record,
                            z_open_id=tokenizer.z_open_id,
                            z_empty_id=tokenizer.z_empty_id,
                            z_close_id=tokenizer.z_close_id,
                        )
                    )
                    latent_rows.append(latent)
            prompt_batch = deps.left_pad_batch(prompts, pad_id=tokenizer.pad_id)
            with deps.bfloat16_context(
                enabled=bool(bundle.config.get("use_bfloat16", False)),
                device=bundle.device,
            ):
                generated = (
                    deps.generate_continuous_latent_sequences(
                        factorization_model=model,
                        input_ids=prompt_batch.input_ids.to(bundle.device),
                        attention_mask=prompt_batch.attention_mask.to(bundle.device),
                        z_vectors=torch.stack(latent_rows).to(bundle.device),
                        sampling_cfg=replace(
                            sampling,
                            seed=generation_seed(
                                rng_mode,
                                base_seed=seed,
                                batch_start=start,
                                phase="analogical",
                            ),
                        ),
                    )
                    .detach()
                    .cpu()
                    .tolist()
                )

            for offset, pair in enumerate(chunk):
                source_text = tokenizer.extract_y_text(generated[2 * offset])
                target_text = tokenizer.extract_y_text(generated[2 * offset + 1])
                source_strategies = strategy_set(task, pair.source, source_text)
                target_strategies = strategy_set(task, pair.target, target_text)
                decisions = analogical_decisions(
                    source_strategies,
                    target_strategies,
                )
                metric_row = {
                    "source_strategies": sorted(source_strategies),
                    "target_strategies": sorted(target_strategies),
                    "decisions": decisions,
                }
                metric_rows.append(metric_row)
                append_jsonl(
                    output_path,
                    {
                        "schema_version": SCHEMA_VERSION,
                        "pair_index": start + offset,
                        "task_name": effective_task_name(task, pair.source),
                        "source_example_id": int(pair.source.example_id),
                        "target_example_id": int(pair.target.example_id),
                        "source_x": jsonable(pair.source.x),
                        "target_x": jsonable(pair.target.x),
                        "source_y_text": source_text,
                        "target_y_text": target_text,
                        **metric_row,
                    },
                )
    return analogical_metrics(metric_rows)


def git_revision(path: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def git_tracked_clean(path: Path) -> bool:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(path),
            "status",
            "--porcelain=v1",
            "--untracked-files=no",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and not result.stdout.strip()


def environment_snapshot(device: Any) -> dict[str, Any]:
    import torch

    payload: dict[str, Any] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": str(torch.__version__),
        "torch_cuda": torch.version.cuda,
        "cudnn": torch.backends.cudnn.version(),
        "device": str(device),
        "cuda_available": bool(torch.cuda.is_available()),
    }
    if device.type == "cuda":
        properties = torch.cuda.get_device_properties(device)
        payload["gpu"] = {
            "name": properties.name,
            "total_memory_bytes": int(properties.total_memory),
            "compute_capability": [int(properties.major), int(properties.minor)],
        }
    return payload


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, default=DEFAULT_UPSTREAM)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--checkpoint-path", default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--rng-mode",
        choices=("released-reseed", "advancing"),
        required=True,
    )
    parser.add_argument("--num-pairs", type=int, default=1024)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--device", default=None)
    return parser


def main(argv: list[str] | None = None) -> Path:
    args = build_arg_parser().parse_args(argv)
    if args.num_pairs < 1:
        raise ValueError("--num-pairs must be at least 1")

    upstream = args.upstream.expanduser().resolve()
    run_dir = args.run_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    deps = load_upstream(upstream)
    run_config = deps.load_run_config(run_dir)
    checkpoint_path = deps.resolve_checkpoint(run_dir, args.checkpoint_path)
    device = deps.resolve_device(args.device)
    batch_size = int(
        run_config["eval_batch_size"] if args.batch_size is None else args.batch_size
    )
    seed = int(run_config["seed"] if args.seed is None else args.seed)
    if batch_size < 1:
        raise ValueError("--batch-size must be at least 1")

    workspace_revision = git_revision(WORKSPACE)
    upstream_revision = git_revision(upstream)
    if workspace_revision is None or upstream_revision is None:
        raise RuntimeError("instrumentation requires Git-bound source trees")
    if not git_tracked_clean(WORKSPACE):
        raise RuntimeError("instrumentation requires a tracked-clean workspace")
    if not git_tracked_clean(upstream):
        raise RuntimeError("instrumentation requires a tracked-clean upstream tree")

    require_new_output_dir(output_dir)
    start_payload = {
        "schema_version": SCHEMA_VERSION,
        "instrumentation_version": INSTRUMENTATION_VERSION,
        "paper_id": "2607.17674",
        "rng_mode": args.rng_mode,
        "seed": seed,
        "batch_size": batch_size,
        "num_pairs": int(args.num_pairs),
        "run_dir": str(run_dir),
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "factorization_config_sha256": sha256_file(run_dir / "config.json"),
        "workspace_revision": workspace_revision,
        "workspace_tracked_clean": True,
        "upstream_revision": upstream_revision,
        "upstream_tracked_clean": True,
        "device": str(device),
        "environment": environment_snapshot(device),
    }
    write_json(output_dir / "run.start.json", start_payload)

    bundle = deps.load_evaluation_bundle(
        run_dir=run_dir,
        checkpoint_path=checkpoint_path,
        device=device,
    )
    records = bundle.responses.test
    if records is None or not records:
        raise ValueError("the benchmark test split is empty")
    sampling = deps.sampling_config(
        run_config=run_config,
        seed=seed,
        tokenizer_runtime=bundle.tokenizer_runtime,
        max_new_tokens=None,
        temperature=None,
        top_k=None,
    )

    fidelity = evaluate_fidelity_traced(
        deps=deps,
        bundle=bundle,
        records=records,
        batch_size=batch_size,
        sampling=sampling,
        seed=seed,
        rng_mode=args.rng_mode,
        output_path=output_dir / "fidelity.jsonl",
    )
    analogical = evaluate_analogical_traced(
        deps=deps,
        bundle=bundle,
        records=records,
        num_pairs=int(args.num_pairs),
        batch_size=batch_size,
        sampling=sampling,
        seed=seed,
        rng_mode=args.rng_mode,
        output_path=output_dir / "analogical.jsonl",
    )
    metrics = {**fidelity, **analogical, "rng_mode": args.rng_mode}
    write_json(output_dir / "metrics.json", metrics)
    artifact_hashes = {
        name: sha256_file(output_dir / name)
        for name in (
            "run.start.json",
            "fidelity.jsonl",
            "analogical.jsonl",
            "metrics.json",
        )
    }
    write_json(
        output_dir / "run.complete.json",
        {
            **start_payload,
            "status": "complete",
            "artifact_sha256": artifact_hashes,
        },
    )
    print(output_dir / "metrics.json")
    return output_dir / "metrics.json"


if __name__ == "__main__":
    main()
