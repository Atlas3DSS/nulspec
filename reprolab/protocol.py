from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


WORKSPACE = Path(__file__).resolve().parents[1]
PROTOCOL_DIR = WORKSPACE / "protocols" / "2607.25091"
CONFIG_PATH = PROTOCOL_DIR / "config.json"
MATRIX_PATH = PROTOCOL_DIR / "matrix.csv"
DATA_MANIFEST_PATH = PROTOCOL_DIR / "data_manifest.json"


@dataclass(frozen=True)
class Arm:
    arm_id: str
    track: str
    model: str
    dataset: str
    seed: int
    initial_state: str


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return load_json(path)


def load_arms(path: Path = MATRIX_PATH) -> list[Arm]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [
        Arm(
            arm_id=row["arm_id"],
            track=row["track"],
            model=row["model"],
            dataset=row["dataset"],
            seed=int(row["seed"]),
            initial_state=row["initial_state"],
        )
        for row in rows
    ]


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def validate_matrix(
    config: dict[str, Any], arms: Iterable[Arm]
) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    expected = {
        (track, model, dataset, 42)
        for track in config["tracks"]
        for model in config["models"]
        for dataset in config["datasets"]
    }
    observed: set[tuple[str, str, str, int]] = set()

    for arm in arms:
        if arm.arm_id in seen:
            errors.append(f"duplicate arm_id: {arm.arm_id}")
        seen.add(arm.arm_id)
        if arm.track not in config["tracks"]:
            errors.append(f"{arm.arm_id}: unknown track {arm.track}")
        if arm.model not in config["models"]:
            errors.append(f"{arm.arm_id}: unknown model {arm.model}")
        if arm.dataset not in config["datasets"]:
            errors.append(f"{arm.arm_id}: unknown dataset {arm.dataset}")
        if arm.seed != 42:
            errors.append(f"{arm.arm_id}: primary seed must be 42")
        observed.add((arm.track, arm.model, arm.dataset, arm.seed))

    missing = sorted(expected - observed)
    extra = sorted(observed - expected)
    errors.extend(f"missing arm: {item}" for item in missing)
    errors.extend(f"unexpected arm: {item}" for item in extra)
    if len(seen) != 30:
        errors.append(f"expected 30 unique arms, found {len(seen)}")
    return errors


def verify_data(
    data_root: Path,
    manifest_path: Path = DATA_MANIFEST_PATH,
) -> list[str]:
    manifest = load_json(manifest_path)
    errors: list[str] = []
    for relative, expected_hash in manifest["files"].items():
        path = data_root / relative
        if not path.is_file():
            errors.append(f"missing data file: {path}")
            continue
        actual_hash = sha256_file(path)
        if actual_hash != expected_hash:
            errors.append(
                f"hash mismatch: {relative}: "
                f"expected {expected_hash}, found {actual_hash}"
            )
    for relative, expected_rows in manifest.get("row_counts", {}).items():
        path = data_root / relative
        if not path.is_file():
            continue
        try:
            value = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"cannot parse row-count file {relative}: {error}")
            continue
        if not isinstance(value, list):
            errors.append(f"expected JSON list for row count: {relative}")
        elif len(value) != expected_rows:
            errors.append(
                f"row-count mismatch: {relative}: "
                f"expected {expected_rows}, found {len(value)}"
            )
    return errors


def extract_prompt_reference(row: dict[str, Any]) -> tuple[str, str]:
    """Match the released evaluator's prompt/reference extraction."""
    if "text" in row:
        text = str(row["text"])
        if "User:" in text and "Assistant:" in text:
            parts = text.split("Assistant:", maxsplit=1)
            prompt = parts[0].replace("User:", "").strip()
            reference = parts[1].strip() if len(parts) > 1 else ""
            return prompt, reference
        return text[:200], text[200:]
    if "prompt" in row:
        prompt = str(row["prompt"])
        reference = row.get("chosen", row.get("response", ""))
        return prompt, str(reference)
    raise ValueError("row has neither 'text' nor 'prompt'")
