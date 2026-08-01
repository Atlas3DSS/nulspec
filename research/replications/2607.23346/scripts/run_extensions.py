#!/usr/bin/env python3
"""Run the frozen SPRKD lowest-loss-ASR and conventional-logit-KD extensions."""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any, Callable

import torch
import torch.nn as nn

from sprkd import (
    MalariaStudentCNN,
    MalariaTeacherCNN,
    aggregate_asr,
    set_seed,
)
from sprkd.data import MalariaDataConfig, make_dataloaders
from sprkd.tli import inject_state_list
from sprkd.training import TrainingHistory, train_response_kd, train_student

from run_trial import (
    atomic_json,
    checkpoint_model,
    environment_payload,
    evaluate,
    history_from_payload,
    history_summary,
    sha256,
)


SCHEMA_VERSION = "nulspec-sprkd-extension-v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--base-output-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--progress", action="store_true")
    return parser.parse_args()


def logits_student() -> MalariaStudentCNN:
    model = MalariaStudentCNN()
    if not isinstance(model.classifier[-1], nn.Softmax):
        raise TypeError("Expected released student to terminate in Softmax.")
    model.classifier[-1] = nn.Identity()
    return model


def logits_teacher() -> MalariaTeacherCNN:
    model = MalariaTeacherCNN()
    if not isinstance(model.classifier[-1], nn.Softmax):
        raise TypeError("Expected released teacher to terminate in Softmax.")
    model.classifier[-1] = nn.Identity()
    return model


def load_state(path: Path, model: nn.Module) -> tuple[nn.Module, dict[str, Any]]:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    model.load_state_dict(payload["model_state_dict"])
    return model, payload


def run_or_load(
    *,
    path: Path,
    name: str,
    factory: Callable[[], nn.Module],
    trainer: Callable[[nn.Module], TrainingHistory],
    device: torch.device,
) -> tuple[nn.Module, TrainingHistory, float, dict[str, Any]]:
    if path.is_file():
        model, payload = load_state(path, factory())
        print(f"[resume] {name}", flush=True)
        return (
            model.to(device),
            history_from_payload(payload),
            float(payload["elapsed_seconds"]),
            payload.get("environment", {}),
        )
    print(f"[stage:start] {name}", flush=True)
    model = factory().to(device)
    started = time.perf_counter()
    history = trainer(model)
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    stage_environment = environment_payload()
    checkpoint_model(
        path,
        model,
        history,
        elapsed,
        {"environment": stage_environment},
    )
    print(f"[stage:complete] {name} seconds={elapsed:.3f}", flush=True)
    return model, history, elapsed, stage_environment


def main() -> None:
    args = parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("Extensions require a CUDA device.")
    if args.seed not in {0, 1, 2, 3, 4}:
        raise ValueError("Frozen extension seeds are exactly 0, 1, 2, 3, and 4.")

    base_trial = args.base_output_root.resolve() / f"seed-{args.seed}"
    base_complete_path = base_trial / "complete.json"
    if not base_complete_path.is_file():
        raise FileNotFoundError(
            f"Base seed {args.seed} is not complete: {base_complete_path}"
        )
    base_complete = json.loads(base_complete_path.read_text())
    base_config = json.loads((base_trial / "config.json").read_text())
    if base_complete.get("complete") is not True:
        raise ValueError("Base trial completion flag is not true.")
    if base_config.get("seed") != args.seed:
        raise ValueError("Base config seed does not match extension seed.")
    if (
        base_config.get("epochs") != 500
        or base_config.get("teacher_epochs") != 2
        or base_config.get("n_teachers") != 3
    ):
        raise ValueError("Base trial does not use the frozen 500/2/3 design.")

    cfg = MalariaDataConfig(
        root=args.data_root.resolve(),
        batch_size=int(base_config["batch_size"]),
        num_workers=int(base_config["num_workers"]),
        seed=args.seed,
    )
    train_loader, valid_loader, dataset = make_dataloaders(cfg)
    saved_split = torch.load(
        base_trial / "split_indices.pth", map_location="cpu", weights_only=False
    )
    if list(train_loader.dataset.indices) != list(saved_split["train_indices"]):
        raise ValueError("Recreated training split differs from the base trial.")
    if list(valid_loader.dataset.indices) != list(saved_split["valid_indices"]):
        raise ValueError("Recreated validation split differs from the base trial.")

    device = torch.device("cuda:0")
    trial_dir = args.output_root.resolve() / f"seed-{args.seed}"
    trial_dir.mkdir(parents=True, exist_ok=True)
    complete_path = trial_dir / "complete.json"
    if complete_path.is_file():
        print(f"[resume] complete extension at {complete_path}", flush=True)
        return

    selected_snapshots = []
    selected_saddles = []
    for index in range(3):
        path = base_trial / "stages" / f"weak_teacher_{index}.pth"
        payload = torch.load(path, map_location="cpu", weights_only=False)
        snapshots = payload["saddle_snapshots"]
        losses = [float(value) for value in payload["saddle_losses"]]
        if len(snapshots) != len(losses) or not snapshots:
            raise ValueError(f"Teacher {index} has invalid snapshot/loss pairing.")
        finite = [
            (position, loss)
            for position, loss in enumerate(losses)
            if math.isfinite(loss)
        ]
        if not finite:
            raise ValueError(f"Teacher {index} has no finite recorded saddle loss.")
        selected_index, selected_loss = min(finite, key=lambda item: item[1])
        selected_snapshots.append(snapshots[selected_index])
        selected_saddles.append(
            {
                "teacher_index": index,
                "snapshot_count": len(snapshots),
                "selected_index": selected_index,
                "selected_loss": selected_loss,
                "last_index": len(snapshots) - 1,
                "last_loss": losses[-1],
            }
        )

    lowest_asr_path = trial_dir / "lowest_loss_asr.pth"
    if lowest_asr_path.is_file():
        lowest_asr = torch.load(lowest_asr_path, map_location="cpu", weights_only=False)
    else:
        lowest_asr = aggregate_asr([[snapshot] for snapshot in selected_snapshots])
        torch.save(lowest_asr, lowest_asr_path)

    target_student = MalariaStudentCNN().to(device)
    carrier_teacher = MalariaTeacherCNN().to(device)
    inject_state_list(target_student, lowest_asr, teacher=carrier_teacher)
    lowest_asr_targets = [
        parameter.detach().clone() for parameter in target_student.parameters()
    ]

    extension_config = {
        "schema_version": SCHEMA_VERSION,
        "seed": args.seed,
        "dataset_samples": len(dataset),
        "epochs": 500,
        "batch_size": cfg.batch_size,
        "num_workers": cfg.num_workers,
        "base_complete_sha256": sha256(base_complete_path),
        "base_config_sha256": sha256(base_trial / "config.json"),
        "base_split_indices_sha256": sha256(base_trial / "split_indices.pth"),
        "selected_saddles": selected_saddles,
        "environment_at_launch": environment_payload(),
    }
    atomic_json(trial_dir / "config.json", extension_config)

    summaries: dict[str, Any] = {}
    models: dict[str, nn.Module] = {}

    def train_lowest_asr(model: nn.Module) -> TrainingHistory:
        _, history = train_student(
            model,
            train_loader,
            valid_loader,
            loss_fn=nn.CrossEntropyLoss(),
            teacher_saddle_points=lowest_asr_targets,
            n_epochs=500,
            lr=0.001,
            device=device,
            progress=args.progress,
        )
        return history

    set_seed(args.seed)
    lowest_model, history, elapsed, stage_environment = run_or_load(
        path=trial_dir / "sprkd_lowest_loss_random_init.pth",
        name="sprkd_lowest_loss_random_init",
        factory=MalariaStudentCNN,
        trainer=train_lowest_asr,
        device=device,
    )
    models["sprkd_lowest_loss_random_init"] = lowest_model
    summaries["sprkd_lowest_loss_random_init"] = {
        **history_summary(history),
        "elapsed_seconds": elapsed,
        "environment": stage_environment,
    }

    weak_teacher, _ = load_state(
        base_trial / "stages" / "weak_teacher_0.pth", logits_teacher()
    )
    weak_teacher = weak_teacher.to(device).eval()

    def train_logit_kd(model: nn.Module) -> TrainingHistory:
        return train_response_kd(
            model,
            weak_teacher,
            train_loader,
            valid_loader,
            n_epochs=500,
            lr=0.001,
            temperature=1.0,
            device=device,
            progress=args.progress,
        )

    set_seed(args.seed)
    logit_model, history, elapsed, stage_environment = run_or_load(
        path=trial_dir / "rkd_conventional_logits.pth",
        name="rkd_conventional_logits",
        factory=logits_student,
        trainer=train_logit_kd,
        device=device,
    )
    models["rkd_conventional_logits"] = logit_model
    summaries["rkd_conventional_logits"] = {
        **history_summary(history),
        "elapsed_seconds": elapsed,
        "environment": stage_environment,
    }

    predictions = {}
    common_targets = None
    for name, model in models.items():
        outcome = evaluate(model, valid_loader, device)
        summaries[name].update(
            {
                "accuracy_sample_weighted": outcome["accuracy_sample_weighted"],
                "cross_entropy_sample_weighted": outcome[
                    "cross_entropy_sample_weighted"
                ],
                "parameter_count": sum(
                    parameter.numel() for parameter in model.parameters()
                ),
            }
        )
        predictions[name] = outcome["predictions"]
        if common_targets is None:
            common_targets = outcome["targets"]
        elif not torch.equal(common_targets, outcome["targets"]):
            raise RuntimeError("Validation target order changed between extensions.")

    torch.save(
        {"targets": common_targets, "predictions": predictions},
        trial_dir / "predictions.pth",
    )
    result = {
        "schema_version": SCHEMA_VERSION,
        "complete": True,
        "seed": args.seed,
        "config_sha256": sha256(trial_dir / "config.json"),
        "models": summaries,
    }
    atomic_json(trial_dir / "results.json", result)
    atomic_json(complete_path, result)
    print(f"[extension:complete] seed={args.seed} path={trial_dir}", flush=True)


if __name__ == "__main__":
    main()
