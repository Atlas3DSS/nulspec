from __future__ import annotations

import argparse
import hashlib
import json
import pickletools
import zipfile
from pathlib import Path
from typing import Any


SCALAR_KEYS = {
    "bf16",
    "fp16",
    "gradient_accumulation_steps",
    "learning_rate",
    "max_seq_length",
    "neftune_noise_alpha",
    "num_train_epochs",
    "per_device_train_batch_size",
    "seed",
    "warmup_ratio",
}
ENUM_KEYS = {"lr_scheduler_type", "optim"}
ALLOWED_GLOBALS = {
    "accelerate.state PartialState",
    "accelerate.utils.dataclasses DistributedType",
    "torch device",
    "transformers.trainer_pt_utils AcceleratorConfig",
    "transformers.trainer_utils HubStrategy",
    "transformers.trainer_utils IntervalStrategy",
    "transformers.trainer_utils SchedulerType",
    "transformers.training_args OptimizerNames",
    "trl.trainer.sft_config SFTConfig",
}
LITERAL_OPS = {
    "BINFLOAT": lambda value: value,
    "BININT": lambda value: value,
    "BININT1": lambda value: value,
    "BININT2": lambda value: value,
    "BINUNICODE": lambda value: value,
    "NEWFALSE": lambda _value: False,
    "NEWTRUE": lambda _value: True,
    "NONE": lambda _value: None,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def data_pickle(path: Path) -> bytes:
    with zipfile.ZipFile(path) as archive:
        members = [
            name for name in archive.namelist() if name.endswith("data.pkl")
        ]
        if len(members) != 1:
            raise ValueError(f"{path}: expected one data.pkl member")
        return archive.read(members[0])


def next_literal(
    operations: list[tuple[pickletools.OpcodeInfo, Any, int]],
    start: int,
    *,
    allow_global_prefix: bool = False,
) -> Any:
    saw_global = False
    for operation, argument, _position in operations[start : start + 12]:
        if operation.name in {"BINPUT", "LONG_BINPUT", "MEMOIZE"}:
            continue
        if operation.name in {"GLOBAL", "STACK_GLOBAL"}:
            saw_global = True
            continue
        converter = LITERAL_OPS.get(operation.name)
        if converter and (not allow_global_prefix or saw_global):
            return converter(argument)
    raise ValueError("no literal found near key")


def inspect_file(path: Path) -> dict[str, Any]:
    operations = list(pickletools.genops(data_pickle(path)))
    globals_seen = sorted(
        {
            str(argument)
            for operation, argument, _position in operations
            if operation.name == "GLOBAL"
        }
    )
    unexpected_globals = sorted(set(globals_seen) - ALLOWED_GLOBALS)
    values: dict[str, Any] = {}
    for index, (operation, argument, _position) in enumerate(operations):
        if operation.name != "BINUNICODE":
            continue
        if argument in SCALAR_KEYS:
            values[str(argument)] = next_literal(operations, index + 1)
        elif argument in ENUM_KEYS:
            values[str(argument)] = next_literal(
                operations, index + 1, allow_global_prefix=True
            )
    return {
        "sha256": sha256(path),
        "values": values,
        "globals": globals_seen,
        "unexpected_globals": unexpected_globals,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect torch-saved TrainingArguments using pickle opcodes only; "
            "the pickle is never executed."
        )
    )
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    files = sorted(args.root.glob("sft/**/training_args.bin"))
    if not files:
        raise SystemExit("no training_args.bin files found")
    result = {
        "schema_version": 1,
        "method": "zipfile + pickletools opcode inspection; no unpickling",
        "files": {
            str(path.relative_to(args.root)): inspect_file(path)
            for path in files
        },
    }
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        if args.output.exists():
            raise SystemExit(f"refusing to overwrite: {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
