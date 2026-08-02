#!/usr/bin/env python3
"""Run the frozen common-probe Hessian trace diagnostic for one base seed."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
from pyhessian import hessian as PyHessian
from sprkd import MalariaStudentCNN, set_seed

from run_trial import atomic_json, environment_payload, sha256


SCHEMA_VERSION = "nulspec-sprkd-hessian-extension-v1"
TESTSET_SHA256 = "f8f19a260a564b258cda59d29c744151cf6f1afb808df2f80456371fa393d08e"
MODEL_STAGES = (
    "control_student",
    "rkd_paper_weak_teacher",
    "rkd_upstream_asr_teacher",
    "sprkd_paper_random_init",
    "sprkd_upstream_direct_init",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-output-root", type=Path, required=True)
    parser.add_argument("--testset", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    return parser.parse_args()


def load_student(path: Path, device: torch.device) -> MalariaStudentCNN:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    model = MalariaStudentCNN()
    model.load_state_dict(payload["model_state_dict"])
    if sum(parameter.numel() for parameter in model.parameters()) != 6_430:
        raise ValueError(f"Unexpected parameter count in {path}.")
    if not isinstance(model.classifier[-1], nn.Softmax):
        raise TypeError(f"Expected released terminal Softmax in {path}.")
    return model.to(device).eval()


def trace_model(
    model: nn.Module,
    data: tuple[torch.Tensor, torch.Tensor],
    *,
    probe_seed: int,
) -> dict[str, Any]:
    set_seed(probe_seed)
    model.zero_grad(set_to_none=True)
    started = time.perf_counter()
    estimator = PyHessian(
        model=model,
        criterion=nn.CrossEntropyLoss(),
        data=data,
        cuda=True,
    )
    # PyHessian's convergence ratio divides by a signed previous trace. A very
    # negative tolerance, rather than zero, guarantees all 100 probes even when
    # an intermediate running trace is negative.
    raw = [float(value) for value in estimator.trace(maxIter=100, tol=-1.0e300)]
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    if len(raw) != 100 or not all(math.isfinite(value) for value in raw):
        raise RuntimeError("Hutchinson estimator did not return 100 finite probes.")
    return {
        "probe_values": raw,
        "trace_mean": statistics.fmean(raw),
        "probe_sample_sd": statistics.stdev(raw),
        "n_probes": len(raw),
        "elapsed_seconds": elapsed,
    }


def main() -> None:
    args = parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("The Hessian diagnostic requires a CUDA device.")
    if args.seed not in {0, 1, 2, 3, 4}:
        raise ValueError("Frozen Hessian seeds are exactly 0 through 4.")

    base_dir = args.base_output_root.resolve() / f"seed-{args.seed}"
    base_complete_path = base_dir / "complete.json"
    if not base_complete_path.is_file():
        raise FileNotFoundError(f"Base seed is incomplete: {base_complete_path}")
    base_complete = json.loads(base_complete_path.read_text())
    if base_complete.get("complete") is not True:
        raise ValueError("Base completion flag is not true.")
    missing = [
        stage
        for stage in MODEL_STAGES
        if not (base_dir / "stages" / f"{stage}.pth").is_file()
    ]
    if missing:
        raise FileNotFoundError(f"Base seed is missing stages: {missing}")

    testset = args.testset.resolve()
    if sha256(testset) != TESTSET_SHA256:
        raise ValueError("TESTSET.pth does not match the frozen SHA-256 digest.")
    inputs, labels = torch.load(testset, map_location="cpu", weights_only=False)
    inputs = torch.as_tensor(inputs)
    labels = torch.as_tensor(labels).long()
    if list(inputs.shape) != [100, 3, 32, 32] or list(labels.shape) != [100]:
        raise ValueError("Unexpected released test-set shape.")
    if not set(labels.tolist()) <= {0, 1}:
        raise ValueError("Released test set contains a non-binary label.")

    output_dir = args.output_root.resolve() / f"seed-{args.seed}"
    output_dir.mkdir(parents=True, exist_ok=True)
    complete_path = output_dir / "complete.json"
    if complete_path.is_file():
        print(f"[resume] complete Hessian extension at {complete_path}", flush=True)
        return

    probe_seed = 100_000 + args.seed
    config = {
        "schema_version": SCHEMA_VERSION,
        "seed": args.seed,
        "base_complete_sha256": sha256(base_complete_path),
        "base_model_sha256s": {
            stage: sha256(base_dir / "stages" / f"{stage}.pth")
            for stage in MODEL_STAGES
        },
        "testset_sha256": TESTSET_SHA256,
        "testset_samples": 100,
        "loss": "CrossEntropyLoss_on_released_terminal_Softmax",
        "probe_distribution": "Rademacher",
        "probe_seed": probe_seed,
        "n_probes": 100,
        "early_stopping_tolerance": -1.0e300,
        "common_probes_within_seed": True,
        "models": list(MODEL_STAGES),
        "environment": environment_payload(),
    }
    config_path = output_dir / "config.json"
    atomic_json(config_path, config)

    device = torch.device("cuda:0")
    data = (inputs.to(device), labels.to(device))
    models = {}
    for stage in MODEL_STAGES:
        print(f"[hessian:start] {stage}", flush=True)
        model = load_student(base_dir / "stages" / f"{stage}.pth", device)
        models[stage] = trace_model(model, data, probe_seed=probe_seed)
        print(
            f"[hessian:complete] {stage} trace={models[stage]['trace_mean']:.8f}",
            flush=True,
        )
        model.zero_grad(set_to_none=True)
        del model
        torch.cuda.empty_cache()

    result = {
        "schema_version": SCHEMA_VERSION,
        "complete": True,
        "seed": args.seed,
        "config_sha256": sha256(config_path),
        "models": models,
    }
    atomic_json(output_dir / "results.json", result)
    atomic_json(complete_path, result)
    print(f"[hessian-extension:complete] seed={args.seed}", flush=True)


if __name__ == "__main__":
    main()
