#!/usr/bin/env python3
"""Verify released SPRKD checkpoints and historical metric traces."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Subset
from torchvision import datasets

from sprkd import load_legacy_metrics_pkl
from sprkd.legacy import load_legacy_checkpoint
from sprkd.stats import pairwise_mcnemar


MODEL_FILES = {
    "sprkd": "SPRKD_MALARIA.pth",
    "control": "CONTROL_MALARIA.pth",
    "rkd": "RKD_MALARIA_STUDENT.pth",
}
METRIC_FILES = {
    "sprkd": "500_SPRKD_LOSSES.pkl",
    "control": "500_CONTROL_STUDENT_LOSSES.pkl",
    "rkd": "RKD_STUDENT_METRICS.pkl",
}
HESSIAN_FILES = {
    "sprkd": ("EIGS_500_SPRKD_MALARIA.pth", 33.39),
    "control": ("EIGS_500_CONTROL_MALARIA.pth", 71.33),
    "rkd": ("EIGS_RKD_MALARIA_STUDENT.pth", 408.27),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--released-root", type=Path, required=True)
    parser.add_argument("--hessian-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--num-workers", type=int, default=4)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def evaluate(model, loader, device: torch.device) -> dict[str, Any]:
    model = model.to(device).eval()
    correct = 0
    total = 0
    loss_sum = 0.0
    predictions = []
    targets = []
    with torch.inference_mode():
        for inputs, labels in loader:
            labels = labels.to(device)
            outputs = model(inputs.to(device))
            predicted = outputs.argmax(1)
            correct += (predicted == labels).sum().item()
            total += labels.numel()
            loss_sum += F.cross_entropy(outputs, labels, reduction="sum").item()
            predictions.append(predicted.cpu())
            targets.append(labels.cpu())
    return {
        "accuracy": 100.0 * correct / total,
        "cross_entropy": loss_sum / total,
        "n_samples": total,
        "predictions": torch.cat(predictions),
        "targets": torch.cat(targets),
    }


def metric_trace_summary(path: Path) -> dict[str, Any]:
    metrics = load_legacy_metrics_pkl(path)
    output: dict[str, Any] = {"sha256": sha256(path)}
    for split in ("TRAINING", "VALIDATION"):
        block = metrics.get(split, {})
        losses = [
            float(value.detach()) if isinstance(value, torch.Tensor) else float(value)
            for value in block.get("LOSSES", [])
        ]
        accuracies = [
            float(value.detach()) if isinstance(value, torch.Tensor) else float(value)
            for value in block.get("ACCURACIES", [])
        ]
        output[split.lower()] = {
            "loss_count": len(losses),
            "accuracy_count": len(accuracies),
            "final_loss_entry": losses[-1] if losses else None,
            "final_accuracy_entry": accuracies[-1] if accuracies else None,
        }
        if split == "VALIDATION" and len(accuracies) >= 108:
            complete_epochs = len(accuracies) // 108
            epoch_accuracies = [
                sum(accuracies[index * 108 : (index + 1) * 108]) / 108
                for index in range(complete_epochs)
            ]
            epoch_losses = [
                sum(losses[index * 108 : (index + 1) * 108]) / 108
                for index in range(min(complete_epochs, len(losses) // 108))
            ]
            # The preserved notebook divides every batch's correct count by 64,
            # including the final 42-sample batch. Because the trace entries are
            # exact multiples of 100/64, integer correct counts and the proper
            # 6,890-sample epoch accuracy can be reconstructed losslessly.
            reconstructed_weighted = []
            for index in range(complete_epochs):
                block_acc = accuracies[index * 108 : (index + 1) * 108]
                correct = sum(round(value * 64 / 100) for value in block_acc)
                reconstructed_weighted.append(100.0 * correct / 6890)
            reconstructed_weighted_losses = []
            for index in range(min(complete_epochs, len(losses) // 108)):
                block_loss = losses[index * 108 : (index + 1) * 108]
                reconstructed_weighted_losses.append(
                    (sum(block_loss[:-1]) * 64 + block_loss[-1] * 42) / 6890
                )
            output["validation"].update(
                {
                    "complete_108_batch_epochs": complete_epochs,
                    "final_epoch_accuracy_unweighted_batch_mean": epoch_accuracies[-1],
                    "best_epoch_accuracy_unweighted_batch_mean": max(epoch_accuracies),
                    "best_epoch_index_zero_based": epoch_accuracies.index(
                        max(epoch_accuracies)
                    ),
                    "final_epoch_loss_unweighted_batch_mean": (
                        epoch_losses[-1] if epoch_losses else None
                    ),
                    "final_epoch_accuracy_reconstructed_sample_weighted": (
                        reconstructed_weighted[-1]
                    ),
                    "best_epoch_accuracy_reconstructed_sample_weighted": max(
                        reconstructed_weighted
                    ),
                    "best_reconstructed_epoch_index_zero_based": (
                        reconstructed_weighted.index(max(reconstructed_weighted))
                    ),
                    "final_epoch_loss_reconstructed_sample_weighted": (
                        reconstructed_weighted_losses[-1]
                    ),
                    "best_epoch_loss_reconstructed_sample_weighted": min(
                        reconstructed_weighted_losses
                    ),
                    "best_loss_epoch_index_zero_based": (
                        reconstructed_weighted_losses.index(
                            min(reconstructed_weighted_losses)
                        )
                    ),
                }
            )
        if split == "VALIDATION" and len(accuracies) >= 323:
            sampled = list(range(322, min(len(losses), len(accuracies)), 323))
            output["validation"]["release_helper_stride_323"] = {
                "sample_count": len(sampled),
                "final_sample_accuracy": accuracies[sampled[-1]],
                "final_sample_loss": losses[sampled[-1]],
            }
    return output


def main() -> None:
    args = parse_args()
    upstream = args.upstream_root.resolve()
    released = args.released_root.resolve()
    hessian_root = (
        args.hessian_root.resolve()
        if args.hessian_root
        else upstream / "METRICS" / "HESSIAN EIGENSPECTRA"
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    testset_path = released / "TESTSET.pth"
    inputs, labels = torch.load(testset_path, map_location="cpu", weights_only=False)
    common_loader = DataLoader(
        torch.utils.data.TensorDataset(inputs, labels), batch_size=256
    )

    output: dict[str, Any] = {
        "schema_version": "nulspec-sprkd-released-verification-v2",
        "device": str(device),
        "testset": {
            "sha256": sha256(testset_path),
            "shape": list(inputs.shape),
            "class_counts": labels.bincount(minlength=2).tolist(),
        },
        "common_100_sample_evaluation": {},
        "serialized_validation_evaluation": {},
        "serialized_split_comparison": {},
        "historical_metric_traces": {},
        "released_hessian_artifacts": {},
    }
    common_predictions: dict[str, torch.Tensor] = {}
    serialized_indices: dict[str, list[int]] = {}

    for label, filename in MODEL_FILES.items():
        checkpoint_path = released / "MODELS" / filename
        learner = load_legacy_checkpoint(checkpoint_path)
        common = evaluate(learner.model, common_loader, device)
        output["common_100_sample_evaluation"][label] = {
            "checkpoint_sha256": sha256(checkpoint_path),
            "accuracy": common["accuracy"],
            "cross_entropy": common["cross_entropy"],
            "parameter_count": sum(
                parameter.numel() for parameter in learner.model.parameters()
            ),
        }
        common_predictions[label] = common["predictions"]

        old_subset = learner.dls.valid.dataset
        old_dataset = old_subset.dataset
        live_dataset = datasets.ImageFolder(
            str(upstream / "cell_images"), transform=old_dataset.transform
        )
        if len(live_dataset) != len(old_dataset):
            raise RuntimeError(f"Dataset length differs for {label}.")
        ordering_matches = all(
            Path(old_path).name == Path(live_path).name and old_class == live_class
            for (old_path, old_class), (live_path, live_class) in zip(
                old_dataset.samples, live_dataset.samples
            )
        )
        if not ordering_matches:
            raise RuntimeError(f"Dataset sample ordering differs for {label}.")
        indices = [int(index) for index in old_subset.indices]
        serialized_indices[label] = indices
        loader = DataLoader(
            Subset(live_dataset, indices),
            batch_size=256,
            shuffle=False,
            num_workers=args.num_workers,
            pin_memory=torch.cuda.is_available(),
        )
        serialized = evaluate(learner.model, loader, device)
        output["serialized_validation_evaluation"][label] = {
            "accuracy": serialized["accuracy"],
            "cross_entropy": serialized["cross_entropy"],
            "n_samples": serialized["n_samples"],
            "sample_order_recovered": ordering_matches,
            "indices_sha256": hashlib.sha256(
                json.dumps(indices, separators=(",", ":")).encode()
            ).hexdigest(),
        }

    output["common_100_sample_mcnemar_exact"] = pairwise_mcnemar(
        common_predictions, labels, method="exact"
    )
    labels_ordered = list(MODEL_FILES)
    for i, left in enumerate(labels_ordered):
        for right in labels_ordered[i + 1 :]:
            left_set = set(serialized_indices[left])
            right_set = set(serialized_indices[right])
            output["serialized_split_comparison"][f"{left}_vs_{right}"] = {
                "identical_order": serialized_indices[left]
                == serialized_indices[right],
                "intersection": len(left_set & right_set),
                "union": len(left_set | right_set),
                "jaccard": len(left_set & right_set) / len(left_set | right_set),
            }

    metrics_root = upstream / "METRICS" / "LOSSES AND ACCURACIES"
    for label, filename in METRIC_FILES.items():
        output["historical_metric_traces"][label] = metric_trace_summary(
            metrics_root / filename
        )

    for label, (filename, reported_trace) in HESSIAN_FILES.items():
        path = hessian_root / filename
        payload = torch.load(path, map_location="cpu", weights_only=False)
        trace = float(payload["TRACE"])
        output["released_hessian_artifacts"][label] = {
            "sha256": sha256(path),
            "trace": trace,
            "paper_reported_trace": reported_trace,
            "difference_from_paper": trace - reported_trace,
            "top_eigenvalues": [float(value) for value in payload["TOP_EIGENVALUES"]],
        }
    hessian = output["released_hessian_artifacts"]
    output["released_hessian_ordering"] = {
        "rkd_largest_matches_paper": (
            hessian["rkd"]["trace"] > hessian["sprkd"]["trace"]
            and hessian["rkd"]["trace"] > hessian["control"]["trace"]
        ),
        "sprkd_lower_than_control_matches_paper": (
            hessian["sprkd"]["trace"] < hessian["control"]["trace"]
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, args.output)
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
