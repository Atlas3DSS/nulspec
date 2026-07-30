# Pre-compute artifact audit

**Audit date:** 2026-07-30

**Status:** complete for protocol v1.0.0

## Source repository

- Public repository: `rezwanh001/SLM-RL-Agents`
- Pinned commit: `64acb621037c711395f2d77516bee70d8a49b819`
- Public history at audit time contains one commit, so conflicting launch
  scripts cannot be ordered using repository history.
- Upstream result file SHA-256:
  `d3897ef87632643b28b076b9d904df918e8b0a40bb6b5f74440e32d771645fbf`
- The upstream result file contains the 15 paper configurations plus three
  instruction-tuned baseline entries. Its paper-model values match the
  manuscript table used by the pilot analysis.

## Released data

The namespace previously recorded as
`rezwanh001/SLM-RL-Agent-Research-Data` returns 401 anonymously and is not
visible to the configured Hub account. A public paper-linked repository exists
at `mr3haque/SLM-RL-Agents-Data`.

- Pinned commit: `2cee50d2989aadebfd5af529937c99f7d539287a`
- Declared license: Apache-2.0
- All 12 split files are present.
- The four TinyStories files byte-match the earlier pilot downloads.
- Hashes and row counts are frozen in `data_manifest.json`.

Wikitext contains 3,996 preference-training and 210 preference-evaluation
pairs rather than the approximately 4,750/250 found in the other corpora. This
matches the released files and is not “filled in” locally.

## Conflicting result artifact

The data repository also contains `results/all_results.json`:

- SHA-256:
  `282920365491ffb758469ee39ed079975266bbfba1445ef5367a244a3edd96d9`
- It contains only six configurations: Pythia-70M and Pythia-160M across the
  three corpora.
- Its numerical values disagree with the manuscript/upstream result table.
  Examples include Pythia-70M/TinyStories PPL 98.65 and reward delta +0.0853,
  versus manuscript values 51.41 and -0.0754.

This file is treated as a distinct, apparently stale or intermediate result
artifact. It is neither deleted nor used as the paper's target table.

## Released model repository

- Repository: `mr3haque/SLM-RL-Agents`
- Pinned commit: `1c74b58663ae3a97117abe60661c72915a6150ed`
- The repository exposes SFT and merged PPO files for all 15 configurations.
- SFT directories include `training_args.bin`.
- PPO directories do not expose an equivalent PPO training-argument record.
- Reward-model checkpoints are not present in the released model tree.

The absence of reward checkpoints prevents exact independent rescoring of the
released PPO models and prevents reconstructing the full released pipeline
solely from published checkpoints.

The Hub's immutable file metadata was captured at the pinned revision without
downloading all 15.8 GB:

- 213 files, 15,811,783,037 bytes in total;
- 47 Git-LFS objects, 15,686,390,904 bytes;
- 15 SFT adapters and 15 merged PPO checkpoints in the primary matrix;
- one additional full Pythia-410M/TinyStories model under `agentic_sft/`;
- no reward-model checkpoint.

The complete repository-metadata digest and every primary checkpoint's LFS
SHA-256 and byte size are frozen in `released_model_manifest.json`. The
inventory can be independently re-queried with
`scripts/inventory_released_models.py`.

All 15 SFT argument files were inspected using `zipfile` and `pickletools`
opcodes without executing their pickle payloads. They confirm the same SFT
settings across the matrix: five epochs, batch 8, accumulation 4, LR 2e-5,
cosine schedule, warmup 0.06, sequence length 512, NEFTune 5, bfloat16, and
seed 42. Digests and extracted constants are in
`released_sft_metadata.json`.

## Environment

The README's stated core versions import and execute a CUDA smoke kernel on the
RTX 4090 after installing `rich`, which is listed in `requirements.txt` but not
installed by the README's core commands or the package's core extras.

The upstream repository publishes lower-bound constraints for most transitive
packages rather than a complete lock. The locally resolved environment is
therefore a documented reconstruction, not proof of the authors' exact
software state.

## README command validation

The published README usage block is not directly executable against the
released CLIs:

| README command | Observed parser result |
|---|---|
| Dataset preparation with `--num_train` and `--num_eval` | Exit 2; both arguments are unrecognized. The script accepts `--max_samples` and `--eval_ratio`. |
| PPO with `--kl_coef 0.1` | Exit 2; `--kl_coef` is unrecognized. The script uses `--kl_penalty` and also requires `--dataset_path`. |
| Evaluation with `--dataset_path` and `--num_samples` | Exit 2; the required argument is `--eval_dataset`; the sample option is `--max_samples`. |

These are documentation defects. The primary runner uses the actual CLI names
and records that choice rather than patching argument aliases into Track R.

The README also states that `scripts/verify_results.py` verifies 339 numeric
fields. At the pinned commit that script exits at parse time because its
`from __future__ import annotations` follows two standalone string literals;
Python permits a future import after only the module docstring. Even after that
one-line source repair, the GitHub release does not contain the referenced
`outputs/*/evaluation_results.json` files, so the claimed raw-output
cross-check cannot be independently executed from the released repository.
Track R preserves this as an upstream artifact failure; it does not patch the
verification claim into success.

## Reported-statistics reconstruction

All 15 reward deltas exactly equal the difference of the rounded PPO and SFT
means. The highlighted confidence intervals and p-values are reproduced by

`SE = sqrt((SD_SFT² + SD_PPO²) / 200)`

followed by a two-sided normal test. The reported win rate is likewise
reproduced as

`Phi(delta / sqrt(SD_SFT² + SD_PPO²))`.

This proves how the released aggregate statistics were calculated, but it does
not make them paired statistics. The formulas treat the two marginal reward
distributions as independent despite evaluating SFT and PPO on the same
prompts. The release does not preserve the full paired score vectors needed to
estimate covariance or reconstruct paired intervals.

The release reports unadjusted tests across 15 configurations. Its three
positive and one negative significant results reproduce at uncorrected
alpha 0.05. After Holm correction, Pythia-410M/TinyStories,
SmolLM2-360M/TinyStories, and Pythia-410M/Wikitext remain significant;
SmolLM2-360M/Wikitext does not (adjusted p = 0.2473).

The exact reconstruction is frozen in `reported_statistics_audit.json` and
generated by `scripts/audit_reported_statistics.py`.
