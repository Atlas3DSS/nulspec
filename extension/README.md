# Three-gate extension implementation

This directory implements the study described in `EXPLAINER.md`.

The completed seed-42 result and interpretation are in `RESULTS.md`. The
18-arm plan is fully executable; six seed-42 arms are complete and the
remaining seed replicates are intentionally left as confirmatory work.

## Components

- `export_pairs.py`: regenerates and preserves all 200 deterministic SFT/PPO
  continuations for any completed arm.
- `make_calibration_pairs.py`: creates a deterministic, held-out
  chosen/rejected calibration set.
- `external_judge.py`: resumable Qwen-27B judging in both A/B orientations.
- `analyze_judgments.py`: position-consistency filtering, paired statistics,
  JSON/Markdown summaries, and a figure.
- `readiness_features.py`: pre-PPO reward discrimination, calibration, and
  FP32/BF16 batch-invariance features.
- `reward_judge_alignment.py`: post-PPO diagnostic comparing the training
  reward's preferred direction with position-consistent Qwen judgments.
- `summarize_training_health.py`: extracts finite/attempted updates, rollback
  outcomes, ratio warnings, and negative-KL warnings from raw PPO logs.
- `outer_teacher.py`: creates a Qwen-record-only audit packet and invokes Codex
  through the existing ChatGPT-authenticated CLI in an ephemeral, read-only
  session. This is the completed historical v1 audit and remains unchanged.
- `review_hierarchy.py`: prospective v2 review hierarchy. It sends the same
  Qwen-only packet independently to GLM and Kimi, then asks Codex to adjudicate
  their traces. GLM currently streams through latency-routed OpenRouter while
  Kimi streams directly from Moonshot AI. Fable is excluded from this recurring
  teacher loop. The runner preserves complete ignored traces and cannot see or
  modify the small models or their outputs.
- `matrixctl.py` and `run_matrix_arm.sh`: the executable three-model ×
  three-seed × two-protocol matrix without overwriting the original runs.

Generated evidence belongs under `artifacts/`; the full matrix belongs under
`matrix_runs/`. All commands are resumable.

Key machine-readable outputs:

- `artifacts/external_judge_summary.json`
- `artifacts/readiness_features.json`
- `artifacts/reward_judge_alignment.json`
- `artifacts/training_health.json`
- `artifacts/outer_teacher_audit.json`
- `artifacts/outer_teacher_packet.json`

## Existing-run external evaluation

```bash
# Export full response pairs for the four completed arms.
bash extension/run_existing_pair_exports.sh

# Build 50 calibration pairs.
python3 \
  extension/make_calibration_pairs.py \
  --data paper_repro/data_release/datasets/tinystories/preference_eval.json \
  --output extension/artifacts/pairs/calibration.json

# Start the guarded Qwen route, then judge every pair twice.
start_remote_llama_pro6000
bash extension/run_external_judging.sh

# Aggregate.
python3 extension/analyze_judgments.py \
  --judgments calibration=extension/artifacts/judgments/calibration.jsonl \
  --judgments exact-70m=extension/artifacts/judgments/exact-70m.jsonl \
  --judgments corrected-70m=extension/artifacts/judgments/corrected-70m.jsonl \
  --judgments exact-410m=extension/artifacts/judgments/exact-410m.jsonl \
  --judgments corrected-410m=extension/artifacts/judgments/corrected-410m.jsonl \
  --calibration-label calibration \
  --output extension/artifacts/external_judge_summary.json \
  --markdown extension/RESULTS.md \
  --plot extension/artifacts/external_judge_results.png

# Review the reviewer with one bounded Codex subscription call.
bash extension/run_outer_teacher.sh

# Prospective hierarchy: Qwen -> parallel GLM/Kimi -> Codex.
# Invalid teacher invocations create logged linked repairs before the join.
# Raw traces are local and ignored; the selected summary path is publishable.
OPENROUTER_API_KEY=... MOONSHOT_API_KEY=... \
  python3 extension/review_hierarchy.py \
  --run-id example-study-date \
  --trace-root .artifacts/review-hierarchy/example-study-date \
  --public-summary extension/artifacts/review_hierarchy_example-study-date.json

python3 extension/validate_review_hierarchy.py \
  --trace-root .artifacts/review-hierarchy/example-study-date \
  --summary extension/artifacts/review_hierarchy_example-study-date.json \
  --output extension/artifacts/review_hierarchy_validation_example-study-date.json

# Compare reward-model direction with the independent judge.
bash extension/run_reward_alignment.sh
```

Fable is intentionally not configured or called in the initial experiment.
Outer-teacher findings are a separate process audit; they never become reward
and do not rewrite Qwen's primary preference estimate.

The direct Codex audit in `RESULTS.md` is historical evidence and is not
reinterpreted as though GLM or Kimi participated. New teacher runs follow
[`docs/REVIEW_HIERARCHY.md`](../docs/REVIEW_HIERARCHY.md): GLM and Kimi audit
Qwen concurrently and Codex adjudicates only after both logical teacher chains
end with valid audits. Invalid invocations remain immutable and are repaired
through linked attempts. Fable is reserved for the separate final-release gate,
where its guardrail refusal is a logged, zero-weight non-response and not a
scientific `HARD_FAIL`.

The validated protocol-v2 reference is
`extension/artifacts/review_hierarchy_20260801_v9.json`, bound to
`extension/artifacts/review_hierarchy_validation_20260801_v9.json`. Earlier
hybrid traces remain available for comparison but are explicitly ineligible in
`extension/artifacts/review_hierarchy_architecture_corrections_20260801.json`.
The separately authorized advisory Fable critique is preserved in
`extension/artifacts/fable_pipeline_critique_20260801_v2.json`; it assessed the
pipeline as `sound_with_changes` and has zero teacher, scientific, release, and
email decision weight.

## Matrix

```bash
python extension/matrixctl.py list
python extension/matrixctl.py write-plan \
  --output extension/artifacts/matrix_plan.json

# One example arm:
bash extension/run_matrix_arm.sh pythia-160m 123 exact 0 "RTX 4090"
bash extension/run_matrix_arm.sh pythia-160m 123 paper-faithful 0 "RTX 4090"
```

The paper-faithful arm refuses to run until its same-seed exact SFT checkpoint
exists. Dev-box arms should be wrapped in the documented `systemd-run` resource
scope from `paper_repro/PROTOCOL.md`.
