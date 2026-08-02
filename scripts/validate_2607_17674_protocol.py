from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
PROTOCOL_ROOT = WORKSPACE / "protocols" / "2607.17674"
CONFIG_PATH = PROTOCOL_ROOT / "config.json"
MATRIX_PATH = PROTOCOL_ROOT / "matrix.csv"
SOURCE_MANIFEST_PATH = PROTOCOL_ROOT / "SOURCE_MANIFEST.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_output(path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def validate_matrix(config: dict[str, object]) -> list[str]:
    errors: list[str] = []
    with MATRIX_PATH.open(newline="") as handle:
        arms = list(csv.DictReader(handle))

    if len(arms) != 4:
        errors.append(f"expected 4 primary arms, found {len(arms)}")
    ids = [arm["arm_id"] for arm in arms]
    if len(set(ids)) != len(ids):
        errors.append("matrix arm IDs are not unique")

    expected_tracks = {"R": "benchmark", "M": "base-model"}
    expected_models = set(config["models"])
    observed_pairs: set[tuple[str, str]] = set()
    for arm in arms:
        track = arm["track"]
        model = arm["model"]
        observed_pairs.add((track, model))
        if track not in expected_tracks:
            errors.append(f"{arm['arm_id']}: unknown track {track}")
        elif arm["response_source"] != expected_tracks[track]:
            errors.append(f"{arm['arm_id']}: response source conflicts with track")
        if model not in expected_models:
            errors.append(f"{arm['arm_id']}: unknown model {model}")
        if arm["objective"] != "global+token":
            errors.append(f"{arm['arm_id']}: unexpected objective")
        if arm["beta"] != "0.01" or arm["beta_schedule"] != "linear-100pct":
            errors.append(f"{arm['arm_id']}: unexpected beta configuration")
        if arm["seed"] != "314159" or arm["initial_state"] != "pending":
            errors.append(f"{arm['arm_id']}: unexpected seed or initial state")

    expected_pairs = {
        (track, model) for track in expected_tracks for model in expected_models
    }
    if observed_pairs != expected_pairs:
        errors.append("matrix does not contain exactly one arm per track/model pair")
    return errors


def validate_upstream(config: dict[str, object], upstream: Path) -> list[str]:
    errors: list[str] = []
    if not (upstream / ".git").exists():
        return [f"missing upstream checkout: {upstream}"]

    expected_revision = config["upstream"]["revision"]
    if git_output(upstream, "rev-parse", "HEAD") != expected_revision:
        errors.append("upstream revision mismatch")
    status_lines = git_output(upstream, "status", "--porcelain").splitlines()
    unexpected_status: list[str] = []
    for line in status_lines:
        relative = line[3:]
        generated_bytecode = (
            "/__pycache__/" in f"/{relative}"
            and relative.endswith((".pyc", "/"))
        )
        generated_runtime = relative.startswith((".data/", ".runs/", ".venv/"))
        if not generated_bytecode and not generated_runtime:
            unexpected_status.append(line)
    if unexpected_status:
        errors.append(
            "upstream checkout has unexpected changes: "
            + "; ".join(unexpected_status)
        )

    manifest = json.loads(SOURCE_MANIFEST_PATH.read_text())
    expected_hashes = manifest["released_config_sha256"]
    for name, expected_hash in expected_hashes.items():
        path = upstream / ("uv.lock" if name == "uv.lock" else f"configs/paper/{name}")
        if not path.is_file():
            errors.append(f"missing upstream artifact: {path}")
        elif sha256_file(path) != expected_hash:
            errors.append(f"upstream artifact hash mismatch: {name}")

    archive = subprocess.run(
        ["git", "-C", str(upstream), "archive", "--format=tar", "HEAD"],
        check=True,
        capture_output=True,
    ).stdout
    archive_hash = hashlib.sha256(archive).hexdigest()
    if archive_hash != config["upstream"]["archive_sha256"]:
        errors.append("upstream Git archive hash mismatch")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--upstream",
        type=Path,
        default=WORKSPACE / "research" / "replications" / "2607.17674" / "work" / "upstream",
    )
    parser.add_argument("--skip-upstream", action="store_true")
    args = parser.parse_args()

    config = json.loads(CONFIG_PATH.read_text())
    errors: list[str] = []
    if config.get("paper_id") != "2607.17674":
        errors.append("paper ID mismatch")
    if config.get("protocol_version") != "1.0.0":
        errors.append("protocol version mismatch")
    errors.extend(validate_matrix(config))
    if not args.skip_upstream:
        errors.extend(validate_upstream(config, args.upstream.resolve()))

    summary = {
        "paper_id": config.get("paper_id"),
        "protocol_version": config.get("protocol_version"),
        "upstream_checked": not args.skip_upstream,
        "errors": errors,
    }
    print(json.dumps(summary, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
