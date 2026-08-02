#!/usr/bin/env python3
"""Run one resumable SPRKD malaria trial under the frozen NULSPEC protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import socket
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn

from sprkd import (
    MalariaStudentCNN,
    MalariaTeacherCNN,
    aggregate_asr,
    set_seed,
)
from sprkd.data import MalariaDataConfig, make_dataloaders
from sprkd.saddle import SaddleCriterion
from sprkd.tli import inject_state_list
from sprkd.training import (
    TrainingHistory,
    train_control,
    train_response_kd,
    train_student,
    train_teacher,
)


SCHEMA_VERSION = "nulspec-sprkd-trial-v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--teacher-epochs", type=int, default=2)
    parser.add_argument("--n-teachers", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--skip-intent-diagnostics", action="store_true")
    parser.add_argument("--skip-control-teacher", action="store_true")
    return parser.parse_args()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def environment_payload() -> dict[str, Any]:
    gpu = {}
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        gpu = {
            "name": torch.cuda.get_device_name(0),
            "compute_capability": f"{props.major}.{props.minor}",
            "total_memory_bytes": props.total_memory,
            "visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        }
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": sys.version,
        "torch": torch.__version__,
        "cuda_runtime": torch.version.cuda,
        "cudnn": torch.backends.cudnn.version(),
        "numpy": np.__version__,
        "gpu": gpu,
    }


def stage_path(trial_dir: Path, stage: str) -> Path:
    return trial_dir / "stages" / f"{stage}.pth"


def history_summary(history: TrainingHistory) -> dict[str, float]:
    return {
        "best_valid_accuracy_unweighted_batch_mean": history.best_valid_acc(),
        "final_valid_accuracy_unweighted_batch_mean": (
            history.valid_accuracies[-1] if history.valid_accuracies else float("nan")
        ),
        "final_valid_loss_unweighted_batch_mean": (
            history.valid_losses[-1] if history.valid_losses else float("nan")
        ),
    }


def evaluate(model: nn.Module, loader, device: torch.device) -> dict[str, Any]:
    model.eval()
    correct = 0
    total = 0
    loss_sum = 0.0
    predictions = []
    targets = []
    with torch.inference_mode():
        for inputs, labels in loader:
            inputs = inputs.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            outputs = model(inputs)
            predicted = outputs.argmax(dim=1)
            loss_sum += nn.functional.cross_entropy(
                outputs, labels, reduction="sum"
            ).item()
            correct += (predicted == labels).sum().item()
            total += labels.numel()
            predictions.append(predicted.cpu())
            targets.append(labels.cpu())
    return {
        "accuracy_sample_weighted": 100.0 * correct / total,
        "cross_entropy_sample_weighted": loss_sum / total,
        "n_samples": total,
        "predictions": torch.cat(predictions),
        "targets": torch.cat(targets),
    }


def checkpoint_model(
    path: Path,
    model: nn.Module,
    history: TrainingHistory,
    elapsed_seconds: float,
    extra: dict[str, Any] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model_state_dict": model.state_dict(),
        "history": history.to_dict(),
        "elapsed_seconds": elapsed_seconds,
    }
    if extra:
        payload.update(extra)
    torch.save(payload, path)


def load_model_stage(path: Path, model: nn.Module) -> tuple[nn.Module, dict[str, Any]]:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    model.load_state_dict(payload["model_state_dict"])
    return model, payload


def history_from_payload(payload: dict[str, Any]) -> TrainingHistory:
    raw = payload["history"]
    return TrainingHistory(
        train_losses=list(raw["TRAINING"]["LOSSES"]),
        train_accuracies=list(raw["TRAINING"]["ACCURACIES"]),
        valid_losses=list(raw["VALIDATION"]["LOSSES"]),
        valid_accuracies=list(raw["VALIDATION"]["ACCURACIES"]),
    )


def run_or_load_student(
    *,
    trial_dir: Path,
    stage: str,
    model: MalariaStudentCNN,
    trainer,
    valid_loader,
    device: torch.device,
) -> tuple[MalariaStudentCNN, TrainingHistory, float]:
    path = stage_path(trial_dir, stage)
    if path.is_file():
        loaded, payload = load_model_stage(path, MalariaStudentCNN())
        print(f"[resume] {stage}", flush=True)
        return (
            loaded.to(device),
            history_from_payload(payload),
            float(payload["elapsed_seconds"]),
        )
    print(f"[stage:start] {stage}", flush=True)
    started = time.perf_counter()
    history = trainer(model)
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    checkpoint_model(path, model, history, elapsed)
    print(f"[stage:complete] {stage} seconds={elapsed:.3f}", flush=True)
    return model, history, elapsed


def main() -> None:
    args = parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("The frozen compute protocol requires a CUDA device.")
    if args.seed not in {0, 1, 2, 3, 4}:
        raise ValueError("Frozen trial seeds are exactly 0, 1, 2, 3, and 4.")
    if args.epochs != 500 or args.teacher_epochs != 2 or args.n_teachers != 3:
        raise ValueError("Paper-faithful run requires 500/2 epochs and 3 teachers.")

    device = torch.device("cuda:0")
    trial_dir = args.output_root.resolve() / f"seed-{args.seed}"
    trial_dir.mkdir(parents=True, exist_ok=True)
    completed = trial_dir / "complete.json"
    if completed.is_file():
        print(f"[resume] complete trial at {completed}", flush=True)
        return

    cfg = MalariaDataConfig(
        root=args.data_root.resolve(),
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        seed=args.seed,
    )
    train_loader, valid_loader, dataset = make_dataloaders(cfg)
    train_indices = list(train_loader.dataset.indices)
    valid_indices = list(valid_loader.dataset.indices)
    config = {
        "schema_version": SCHEMA_VERSION,
        "seed": args.seed,
        "epochs": args.epochs,
        "teacher_epochs": args.teacher_epochs,
        "n_teachers": args.n_teachers,
        "batch_size": args.batch_size,
        "num_workers": args.num_workers,
        "train_fraction": cfg.train_fraction,
        "dataset_samples": len(dataset),
        "train_samples": len(train_indices),
        "valid_samples": len(valid_indices),
        "learning_rate": 0.001,
        "saddle_steps": 1,
        "n_top_eigs": 4,
        "saddle_rule": "magnitude",
        "saddle_magnitude_threshold": 7.0,
        "upstream_commit": "7f1655ff1295c9a6dcf8d24f6410a036cd7e3497",
        "environment": environment_payload(),
    }
    atomic_json(trial_dir / "config.json", config)
    torch.save(
        {"train_indices": train_indices, "valid_indices": valid_indices},
        trial_dir / "split_indices.pth",
    )

    summaries: dict[str, Any] = {}
    models: dict[str, nn.Module] = {}
    predictions: dict[str, torch.Tensor] = {}
    common_targets: torch.Tensor | None = None

    teacher_models: list[MalariaTeacherCNN] = []
    repositories: list[list[list[torch.Tensor]]] = []
    for index in range(args.n_teachers):
        stage = f"weak_teacher_{index}"
        path = stage_path(trial_dir, stage)
        if path.is_file():
            model, payload = load_model_stage(path, MalariaTeacherCNN())
            history = history_from_payload(payload)
            snapshots = payload["saddle_snapshots"]
            elapsed = float(payload["elapsed_seconds"])
            print(f"[resume] {stage}", flush=True)
        else:
            print(f"[stage:start] {stage}", flush=True)
            set_seed(args.seed + index)
            model = MalariaTeacherCNN().to(device)
            started = time.perf_counter()
            optimizer, history = train_teacher(
                model,
                train_loader,
                valid_loader,
                loss_fn=nn.CrossEntropyLoss(),
                n_epochs=args.teacher_epochs,
                lr=0.001,
                saddle_steps=1,
                n_top_eigs=4,
                device=device,
                progress=args.progress,
                sprkd_kwargs={
                    "saddle_criterion": SaddleCriterion(
                        rule="magnitude", magnitude_threshold=7.0
                    )
                },
            )
            if len(optimizer.saddle_repository) == 0:
                optimizer.saddle_repository.append(
                    list(model.parameters()), loss=float(history.train_losses[-1])
                )
            torch.cuda.synchronize()
            elapsed = time.perf_counter() - started
            snapshots = optimizer.saddle_repository.snapshots
            checkpoint_model(
                path,
                model,
                history,
                elapsed,
                {
                    "saddle_snapshots": snapshots,
                    "saddle_losses": optimizer.saddle_repository.losses,
                },
            )
            print(
                f"[stage:complete] {stage} seconds={elapsed:.3f} "
                f"saddles={len(snapshots)}",
                flush=True,
            )
        model = model.to(device)
        evaluation = evaluate(model, valid_loader, device)
        summaries[stage] = {
            **history_summary(history),
            "accuracy_sample_weighted": evaluation["accuracy_sample_weighted"],
            "cross_entropy_sample_weighted": evaluation[
                "cross_entropy_sample_weighted"
            ],
            "elapsed_seconds": elapsed,
            "saddle_count": len(snapshots),
        }
        teacher_models.append(model)
        repositories.append(snapshots)

    asr_path = stage_path(trial_dir, "asr")
    if asr_path.is_file():
        asr = torch.load(asr_path, map_location="cpu", weights_only=False)
        print("[resume] asr", flush=True)
    else:
        asr = aggregate_asr(repositories)
        torch.save(asr, asr_path)
        print("[stage:complete] asr", flush=True)

    # Exact script behavior: injection directly initializes the trained student
    # and mutates teacher_models[0] to the averaged ASR.
    set_seed(args.seed)
    upstream_student = MalariaStudentCNN().to(device)
    inject_state_list(upstream_student, asr, teacher=teacher_models[0])
    targets = [
        parameter.detach().clone() for parameter in upstream_student.parameters()
    ]
    asr_teacher_eval = evaluate(teacher_models[0], valid_loader, device)
    summaries["asr_mutated_teacher"] = {
        "accuracy_sample_weighted": asr_teacher_eval["accuracy_sample_weighted"],
        "cross_entropy_sample_weighted": asr_teacher_eval[
            "cross_entropy_sample_weighted"
        ],
    }

    def sprkd_train(model: MalariaStudentCNN) -> TrainingHistory:
        _, history = train_student(
            model,
            train_loader,
            valid_loader,
            loss_fn=nn.CrossEntropyLoss(),
            teacher_saddle_points=targets,
            n_epochs=args.epochs,
            lr=0.001,
            device=device,
            progress=args.progress,
        )
        return history

    upstream_student, history, elapsed = run_or_load_student(
        trial_dir=trial_dir,
        stage="sprkd_upstream_direct_init",
        model=upstream_student,
        trainer=sprkd_train,
        valid_loader=valid_loader,
        device=device,
    )
    models["sprkd_upstream_direct_init"] = upstream_student
    summaries["sprkd_upstream_direct_init"] = {
        **history_summary(history),
        "elapsed_seconds": elapsed,
    }

    if not args.skip_intent_diagnostics:
        set_seed(args.seed)
        intent_student = MalariaStudentCNN().to(device)
        intent_student, history, elapsed = run_or_load_student(
            trial_dir=trial_dir,
            stage="sprkd_paper_random_init",
            model=intent_student,
            trainer=sprkd_train,
            valid_loader=valid_loader,
            device=device,
        )
        models["sprkd_paper_random_init"] = intent_student
        summaries["sprkd_paper_random_init"] = {
            **history_summary(history),
            "elapsed_seconds": elapsed,
        }

    set_seed(args.seed)
    control_student = MalariaStudentCNN().to(device)

    def control_student_train(model: MalariaStudentCNN) -> TrainingHistory:
        return train_control(
            model,
            train_loader,
            valid_loader,
            loss_fn=nn.CrossEntropyLoss(),
            n_epochs=args.epochs,
            lr=0.001,
            device=device,
            progress=args.progress,
        )

    control_student, history, elapsed = run_or_load_student(
        trial_dir=trial_dir,
        stage="control_student",
        model=control_student,
        trainer=control_student_train,
        valid_loader=valid_loader,
        device=device,
    )
    models["control_student"] = control_student
    summaries["control_student"] = {
        **history_summary(history),
        "elapsed_seconds": elapsed,
    }

    # Exact released script: response KD uses teacher 0 after it was overwritten
    # by ASR injection above.
    set_seed(args.seed)
    rkd_upstream = MalariaStudentCNN().to(device)

    def rkd_upstream_train(model: MalariaStudentCNN) -> TrainingHistory:
        return train_response_kd(
            model,
            teacher_models[0],
            train_loader,
            valid_loader,
            n_epochs=args.epochs,
            lr=0.001,
            temperature=1.0,
            device=device,
            progress=args.progress,
        )

    rkd_upstream, history, elapsed = run_or_load_student(
        trial_dir=trial_dir,
        stage="rkd_upstream_asr_teacher",
        model=rkd_upstream,
        trainer=rkd_upstream_train,
        valid_loader=valid_loader,
        device=device,
    )
    models["rkd_upstream_asr_teacher"] = rkd_upstream
    summaries["rkd_upstream_asr_teacher"] = {
        **history_summary(history),
        "elapsed_seconds": elapsed,
    }

    if not args.skip_intent_diagnostics:
        weak_teacher, _ = load_model_stage(
            stage_path(trial_dir, "weak_teacher_0"), MalariaTeacherCNN()
        )
        weak_teacher = weak_teacher.to(device).eval()
        set_seed(args.seed)
        rkd_weak = MalariaStudentCNN().to(device)

        def rkd_weak_train(model: MalariaStudentCNN) -> TrainingHistory:
            return train_response_kd(
                model,
                weak_teacher,
                train_loader,
                valid_loader,
                n_epochs=args.epochs,
                lr=0.001,
                temperature=1.0,
                device=device,
                progress=args.progress,
            )

        rkd_weak, history, elapsed = run_or_load_student(
            trial_dir=trial_dir,
            stage="rkd_paper_weak_teacher",
            model=rkd_weak,
            trainer=rkd_weak_train,
            valid_loader=valid_loader,
            device=device,
        )
        models["rkd_paper_weak_teacher"] = rkd_weak
        summaries["rkd_paper_weak_teacher"] = {
            **history_summary(history),
            "elapsed_seconds": elapsed,
        }

    if not args.skip_control_teacher:
        control_teacher_path = stage_path(trial_dir, "control_teacher")
        if control_teacher_path.is_file():
            control_teacher, payload = load_model_stage(
                control_teacher_path, MalariaTeacherCNN()
            )
            history = history_from_payload(payload)
            elapsed = float(payload["elapsed_seconds"])
            print("[resume] control_teacher", flush=True)
        else:
            print("[stage:start] control_teacher", flush=True)
            set_seed(args.seed)
            control_teacher = MalariaTeacherCNN().to(device)
            started = time.perf_counter()
            history = train_control(
                control_teacher,
                train_loader,
                valid_loader,
                loss_fn=nn.CrossEntropyLoss(),
                n_epochs=args.epochs,
                lr=0.001,
                device=device,
                progress=args.progress,
            )
            torch.cuda.synchronize()
            elapsed = time.perf_counter() - started
            checkpoint_model(control_teacher_path, control_teacher, history, elapsed)
            print(
                f"[stage:complete] control_teacher seconds={elapsed:.3f}",
                flush=True,
            )
        models["control_teacher"] = control_teacher.to(device)
        summaries["control_teacher"] = {
            **history_summary(history),
            "elapsed_seconds": elapsed,
        }

    for name, model in models.items():
        evaluation = evaluate(model, valid_loader, device)
        summaries[name].update(
            {
                "accuracy_sample_weighted": evaluation["accuracy_sample_weighted"],
                "cross_entropy_sample_weighted": evaluation[
                    "cross_entropy_sample_weighted"
                ],
                "parameter_count": sum(p.numel() for p in model.parameters()),
            }
        )
        predictions[name] = evaluation["predictions"]
        if common_targets is None:
            common_targets = evaluation["targets"]
        elif not torch.equal(common_targets, evaluation["targets"]):
            raise RuntimeError("Validation target order changed between models.")

    torch.save(
        {"targets": common_targets, "predictions": predictions},
        trial_dir / "predictions.pth",
    )
    result = {
        "schema_version": SCHEMA_VERSION,
        "seed": args.seed,
        "config_sha256": sha256(trial_dir / "config.json"),
        "models": summaries,
    }
    atomic_json(trial_dir / "results.json", result)
    atomic_json(completed, {"complete": True, **result})
    print(f"[trial:complete] seed={args.seed} path={trial_dir}", flush=True)


if __name__ == "__main__":
    main()
