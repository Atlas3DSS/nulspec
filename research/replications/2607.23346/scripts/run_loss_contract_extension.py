#!/usr/bin/env python3
"""Run the post-hoc supervised-logit loss-contract diagnostic for one seed."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Callable

import torch
import torch.nn as nn

from sprkd import MalariaStudentCNN, MalariaTeacherCNN, set_seed
from sprkd.data import MalariaDataConfig, make_dataloaders
from sprkd.tli import inject_state_list
from sprkd.training import TrainingHistory, train_control, train_student

from run_trial import (
    atomic_json,
    checkpoint_model,
    environment_payload,
    evaluate,
    history_from_payload,
    history_summary,
    sha256,
)


SCHEMA_VERSION = "nulspec-sprkd-loss-contract-extension-v1"
MODEL_STAGES = (
    "control_student_logit_ce",
    "sprkd_logit_ce_random_init",
)


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


def run_or_load(
    *,
    path: Path,
    name: str,
    trainer: Callable[[MalariaStudentCNN], tuple[TrainingHistory, dict[str, Any]]],
    device: torch.device,
) -> tuple[MalariaStudentCNN, TrainingHistory, float, dict[str, Any]]:
    if path.is_file():
        payload = torch.load(path, map_location="cpu", weights_only=False)
        model = logits_student()
        model.load_state_dict(payload["model_state_dict"])
        print(f"[resume] {name}", flush=True)
        return (
            model.to(device),
            history_from_payload(payload),
            float(payload["elapsed_seconds"]),
            dict(payload.get("diagnostic_metadata") or {}),
        )
    print(f"[stage:start] {name}", flush=True)
    model = logits_student().to(device)
    started = time.perf_counter()
    history, diagnostic_metadata = trainer(model)
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    checkpoint_model(
        path,
        model,
        history,
        elapsed,
        {
            "diagnostic_metadata": diagnostic_metadata,
            "environment": environment_payload(),
        },
    )
    print(f"[stage:complete] {name} seconds={elapsed:.3f}", flush=True)
    return model, history, elapsed, diagnostic_metadata


def main() -> int:
    args = parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("The loss-contract extension requires a CUDA device.")
    if args.seed not in {0, 1, 2, 3, 4}:
        raise ValueError("Frozen seeds are exactly 0 through 4.")

    base_dir = args.base_output_root.resolve() / f"seed-{args.seed}"
    base_complete_path = base_dir / "complete.json"
    if not base_complete_path.is_file():
        raise FileNotFoundError(f"Base seed is incomplete: {base_complete_path}")
    base_complete = json.loads(base_complete_path.read_text())
    base_config_path = base_dir / "config.json"
    base_config = json.loads(base_config_path.read_text())
    if (
        base_complete.get("complete") is not True
        or base_config.get("seed") != args.seed
    ):
        raise ValueError("Base completion/config metadata differs from the seed.")
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
    split_path = base_dir / "split_indices.pth"
    saved_split = torch.load(split_path, map_location="cpu", weights_only=False)
    if list(train_loader.dataset.indices) != list(saved_split["train_indices"]):
        raise ValueError("Recreated training split differs from the base trial.")
    if list(valid_loader.dataset.indices) != list(saved_split["valid_indices"]):
        raise ValueError("Recreated validation split differs from the base trial.")

    asr_path = base_dir / "stages" / "asr.pth"
    asr = torch.load(asr_path, map_location="cpu", weights_only=False)
    set_seed(args.seed)
    target_student = MalariaStudentCNN()
    carrier_teacher = MalariaTeacherCNN()
    inject_state_list(target_student, asr, teacher=carrier_teacher)
    target_parameters = [
        parameter.detach().clone() for parameter in target_student.parameters()
    ]

    output_dir = args.output_root.resolve() / f"seed-{args.seed}"
    output_dir.mkdir(parents=True, exist_ok=True)
    complete_path = output_dir / "complete.json"
    if complete_path.is_file():
        print(f"[resume] complete loss-contract extension at {complete_path}")
        return 0

    base_stage_hashes = {
        path.stem: sha256(path) for path in sorted((base_dir / "stages").glob("*.pth"))
    }
    config = {
        "schema_version": SCHEMA_VERSION,
        "seed": args.seed,
        "dataset_samples": len(dataset),
        "epochs": 500,
        "batch_size": cfg.batch_size,
        "num_workers": cfg.num_workers,
        "learning_rate": 0.001,
        "base_complete_sha256": sha256(base_complete_path),
        "base_config_sha256": sha256(base_config_path),
        "base_split_indices_sha256": sha256(split_path),
        "base_stage_sha256s": base_stage_hashes,
        "asr_sha256": sha256(asr_path),
        "one_change": (
            "Replace the released terminal Softmax with Identity so "
            "CrossEntropyLoss receives logits; all other supervised-training "
            "settings remain unchanged."
        ),
        "specified_after_completed_seeds": [0, 1, 2],
        "interpretation": "post_hoc_outcome_motivated_diagnostic",
        "environment_at_launch": environment_payload(),
    }
    config_path = output_dir / "config.json"
    atomic_json(config_path, config)

    device = torch.device("cuda:0")
    models: dict[str, MalariaStudentCNN] = {}
    summaries: dict[str, Any] = {}

    def train_control_logits(
        model: MalariaStudentCNN,
    ) -> tuple[TrainingHistory, dict[str, Any]]:
        history = train_control(
            model,
            train_loader,
            valid_loader,
            loss_fn=nn.CrossEntropyLoss(),
            n_epochs=500,
            lr=0.001,
            device=device,
            progress=args.progress,
        )
        return history, {"optimizer": "Adam", "terminal_activation": "Identity"}

    set_seed(args.seed)
    control, history, elapsed, diagnostic = run_or_load(
        path=output_dir / "control_student_logit_ce.pth",
        name="control_student_logit_ce",
        trainer=train_control_logits,
        device=device,
    )
    models["control_student_logit_ce"] = control
    summaries["control_student_logit_ce"] = {
        **history_summary(history),
        "elapsed_seconds": elapsed,
        "diagnostic_metadata": diagnostic,
    }

    def train_sprkd_logits(
        model: MalariaStudentCNN,
    ) -> tuple[TrainingHistory, dict[str, Any]]:
        optimizer, history = train_student(
            model,
            train_loader,
            valid_loader,
            loss_fn=nn.CrossEntropyLoss(),
            teacher_saddle_points=target_parameters,
            n_epochs=500,
            lr=0.001,
            device=device,
            progress=args.progress,
        )
        return history, {
            "optimizer": "SPRKD(Adam)",
            "terminal_activation": "Identity",
            "sprkd_final_state": optimizer.state_dict().get("sprkd_extra", {}),
        }

    set_seed(args.seed)
    sprkd, history, elapsed, diagnostic = run_or_load(
        path=output_dir / "sprkd_logit_ce_random_init.pth",
        name="sprkd_logit_ce_random_init",
        trainer=train_sprkd_logits,
        device=device,
    )
    models["sprkd_logit_ce_random_init"] = sprkd
    summaries["sprkd_logit_ce_random_init"] = {
        **history_summary(history),
        "elapsed_seconds": elapsed,
        "diagnostic_metadata": diagnostic,
    }

    predictions: dict[str, torch.Tensor] = {}
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
            raise RuntimeError("Validation target order changed between models.")

    torch.save(
        {"targets": common_targets, "predictions": predictions},
        output_dir / "predictions.pth",
    )
    result = {
        "schema_version": SCHEMA_VERSION,
        "complete": True,
        "seed": args.seed,
        "config_sha256": sha256(config_path),
        "models": summaries,
    }
    atomic_json(output_dir / "results.json", result)
    atomic_json(complete_path, result)
    print(f"[loss-contract-extension:complete] seed={args.seed}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
