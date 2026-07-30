from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from peft import LoraConfig, TaskType, get_peft_model
from transformers import AutoModelForSequenceClassification


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sft-adapter", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    torch.manual_seed(42)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.sft_adapter,
        num_labels=1,
    )
    module_name = "gpt_neox.layers.0.attention.dense"
    before_module = model.get_submodule(module_name)
    before_a = before_module.lora_A["default"].weight.detach().clone()
    before_b = before_module.lora_B["default"].weight.detach().clone()

    sft_config = json.loads(
        (args.sft_adapter / "adapter_config.json").read_text()
    )
    reward_config = LoraConfig(
        r=sft_config["r"],
        lora_alpha=sft_config["lora_alpha"],
        lora_dropout=0.05,
        target_modules="all-linear",
        task_type=TaskType.SEQ_CLS,
    )
    wrapped = get_peft_model(model, reward_config)
    after_module = wrapped.base_model.model.get_submodule(module_name)
    after_a = after_module.lora_A["default"].weight.detach()
    after_b = after_module.lora_B["default"].weight.detach()

    result = {
        "operation": (
            "AutoModelForSequenceClassification.from_pretrained(SFT adapter), "
            "then get_peft_model(..., adapter_name='default')"
        ),
        "module": module_name,
        "sft_lora_a_norm_before": float(before_a.norm()),
        "sft_lora_b_norm_before": float(before_b.norm()),
        "lora_a_norm_after": float(after_a.norm()),
        "lora_b_norm_after": float(after_b.norm()),
        "lora_a_max_absolute_change": float((before_a - after_a).abs().max()),
        "lora_b_max_absolute_change": float((before_b - after_b).abs().max()),
        "sft_a_preserved": torch.equal(before_a, after_a),
        "sft_b_preserved": torch.equal(before_b, after_b),
        "conclusion": (
            "The release path overwrites the loaded SFT adapter before reward "
            "training; the new LoRA B matrix is reinitialized to zero."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
