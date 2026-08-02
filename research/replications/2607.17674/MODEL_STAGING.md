# Pinned base-model snapshot staging

Both paper model inputs were acquired by immutable Hugging Face revision before
the first primary arm produced a standalone evaluation result. Snapshot
contents are kept in ignored study storage; this tracked record publishes the
content-manifest identities needed to verify another acquisition.

| Model | Pinned revision | Snapshot files | Bytes | Snapshot-manifest SHA-256 | `model.safetensors` SHA-256 |
| --- | --- | ---: | ---: | --- | --- |
| Qwen/Qwen2.5-0.5B | `060db6499f32faf8b98477b0a26969ef7d8b9987` | 10 | 999,602,900 | `80f87879b12422e89a2cdcfda152fe4d9a6b154996410b7684169cca66e4cfdc` | `88c142557820ccad55bb59756bfcfcf891de9cc6202816bd346445188a0ed342` |
| Qwen/Qwen2.5-1.5B | `8faed761d45a263340a0528343f099c05c9a4323` | 10 | 3,098,972,223 | `bc3af4ec8b5186f28fe3d9cf3d9207b7cc6909b034b0f057679a6502ee6c7bcc` | `a961db72e75d52b18e6b0c9d379e51a26973b233385e0e127fdda7d648aec796` |

The manifests were generated with `scripts/hash_artifact_tree.py`, excluding
only Hugging Face's local `.cache/` transfer metadata. They include the ten
repository artifacts consumed by Transformers: model/configuration files,
tokenizer files, model card, license, and Git attributes. The 1.5B snapshot was
downloaded under a low-priority 4 GiB system-memory cap while the 0.5B arm was
running; it did not start another GPU workload.

The runner resolves these exact directories from the model key and revision in
`protocols/2607.17674/config.json`. Network access is disabled before any
training process begins, so a mutable Hub reference cannot be consulted during
an arm.
