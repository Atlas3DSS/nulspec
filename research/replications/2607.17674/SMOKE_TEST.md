# Upstream executable-artifact smoke test

**Registered run:** <https://github.com/Atlas3DSS/nulspec/issues/27>

**Protocol:** `2607.17674-protocol-v1.0.0`

**Source revision:** `0c0f221d7dc37cd4eb7fb1af3332520bccf4d9fe`

**Outcome:** passed on 2026-08-01. All four upstream README commands completed
on CPU without a source patch: small benchmark generation, random base-model
training, factorization training, and standalone evaluation.

The smoke example intentionally trains only a tiny one-layer model for two
base-model steps and four factorization steps. Its final Distributional
Fidelity and Analogical Consistency were both 0.0. Those values demonstrate
that the metric path executes; they are not evidence for or against the paper.

## Frozen environment observed

- Python 3.12.12
- PyTorch 2.10.0+cu128
- Transformers 5.2.0
- PEFT 0.18.1
- NumPy 2.4.2
- PyArrow 23.0.1

## Ignored artifact manifests

- generated data: 28 files, 158,157 bytes; manifest SHA-256
  `4fe0df2b9d7e51a97d2bfbda9041758fd60b4d9d9f15343c12724247de3c831f`;
- run outputs: 21 files, 5,714,898 bytes; manifest SHA-256
  `dd35d74bbcda8626b4c47d8f98e9266a66955e03261e2d7a9efb04632de725c9`;
- logs and supporting manifests: 7 files, 38,337 bytes at capture; manifest
  SHA-256
  `e5c5330da2ba125b6e8b3257f019c0f0901415b1048c02302275eeee2b6bd2ca`;
- final evaluator metrics JSON SHA-256
  `eae7400352f249e3edd870931d4ff9bc600e950c1128c6752962d7e89e05f4cb`.

Large/generated files remain beneath ignored `work/` paths. The Git record
contains only this summary and their content digests.
