from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
HASHER = WORKSPACE / "scripts/hash_artifact_tree.py"
RUNNER = WORKSPACE / "scripts/run_2607_17674_arm.sh"


def test_hash_artifact_tree_records_exact_base_input(tmp_path: Path) -> None:
    base = tmp_path / "base_model"
    (base / "final_model").mkdir(parents=True)
    model = base / "final_model" / "model.safetensors"
    marker = base / "base.complete.json"
    model.write_bytes(b"model bytes")
    marker.write_text('{"complete":true}\n')
    output = tmp_path / "base-manifest.json"

    subprocess.run(
        [sys.executable, str(HASHER), str(base), "--output", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )
    manifest = json.loads(output.read_text())
    records = {item["path"]: item for item in manifest["files"]}
    assert set(records) == {"base.complete.json", "final_model/model.safetensors"}
    assert records["final_model/model.safetensors"]["sha256"] == hashlib.sha256(
        b"model bytes"
    ).hexdigest()
    assert manifest["total_bytes"] == model.stat().st_size + marker.stat().st_size


def test_primary_runner_hashes_base_before_factorization() -> None:
    source = RUNNER.read_text()
    manifest_position = source.index("BASE_INPUT_MANIFEST=")
    factorization_position = source.index('FACTORIZATION_DIR="$RUN_ROOT/factorization"')
    assert manifest_position < factorization_position
    assert 'source_arm: $source_arm' in source
    assert 'source_attempt: $source_attempt' in source
