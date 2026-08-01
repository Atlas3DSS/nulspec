# Source and artifact manifest

Fetched 2026-07-31. Binary inputs are intentionally not committed; these hashes
identify the exact material used.

| Artifact | SHA-256 |
|---|---|
| arXiv abstract HTML | `d60aee39d19341cf642d889540558cd80168f97d1877881f88cf9fc04b6afd29` |
| arXiv PDF | `f9ad5d1a4a12a930d0fd94913b2c4b28b738f203ad9b28fb58599a900e07a8db` |
| arXiv source tar | `b7f25d66b8b4947f609951bc1a424a0cfcb2d5cc0c2e5de59c94b27c3dffa6dd` |
| `TESTSET.pth` | `f8f19a260a564b258cda59d29c744151cf6f1afb808df2f80456371fa393d08e` |
| released SPRKD checkpoint | `cf218a350c4cd81661ba3efe517b096beeb72b38647ec80973706789ac75314d` |
| released Control-S checkpoint | `b79eb99815065401c2f66b3c54fecff44ecf1136b96897ede6df792e73da7aff` |
| released RKD checkpoint | `8a2368c288e021865dbc5b50a541eccd87b4f949be36b9837f61ab65d95f08b4` |
| released teacher saddle repository | `adbb032696c9572bb10ab9c097965d6c38906ecb151ebe3fda7c5ba07250a1ee` |
| released weak-teacher checkpoint | `0e492e6d8c6e74b33476804120a7e9a30c10ed2e78636e3b55e1b484c19560f7` |
| historical 500-epoch SPRKD metrics | `68b13de8f32ba74460e4eb4bdf414995b28bf099aecbc758b3e87bda0ca8f443` |
| historical 500-epoch Control-S metrics | `5b8dec1d73b4ca9db4594a59c5643bdd2ed7857bb594cbf75025628671bf6ae8` |
| historical RKD metrics | `7dd822d18a2b5f96981810826f16db65378d206608bd58a6afce05838eb61014` |
| released 500-epoch SPRKD Hessian artifact | `76de32cb1b004f0bed54c62b74be23de85c9dd71eae57f93bd1fd61cec6cdb8b` |
| released 500-epoch Control-S Hessian artifact | `2f2fb29813c216ebb7954b8d2c239d6501dd81a1349dd7d70e82e0f51eb2e425` |
| released RKD Hessian artifact | `9d3f8d813f85fb96b56157b3e13bb5e58c10961802ce424826c64ba629736808` |
| CUDA container base index | `ac55d124da4882b497f732d8dfd9a702d5447a5f29d08d56da6f64f0a1eb34bc` |

Upstream Git commit:
`7f1655ff1295c9a6dcf8d24f6410a036cd7e3497`

The dataset contains 27,558 PNG images. Its deterministic manifest digest is
computed by sorting relative PNG paths, hashing every file with `sha256sum`,
then hashing the resulting manifest stream:
`4fc7205c482dd43959cf1795ccbdbc0f819c1001dca374a0ee14eb9a3d5c1381`.

Acquisition URLs:

- `https://arxiv.org/abs/2607.23346v1`
- `https://arxiv.org/pdf/2607.23346v1`
- `https://export.arxiv.org/e-print/2607.23346v1`
- `https://github.com/thetechdude124/SADDLE-POINT-RECRUITMENT-FOR-KNOWLEDGE-DISTILLATION`

Git-LFS objects were downloaded from GitHub's public media endpoint at the
frozen commit and verified against the SHA-256 OIDs embedded in their pointer
files.

## Rights and redistribution boundary

The upstream code repository declares the MIT License in its checked-in
`LICENSE`. The arXiv record exposes the paper under CC BY 4.0. The official NLM
pages make the malaria archive publicly downloadable and request source
attribution, but the pages inspected for this study do not state a separate
redistribution license for the image archive. NULSPEC therefore publishes the
official acquisition URL, file manifest, and digest—not a copy of the images.
The ignored released checkpoints are likewise reacquired from their original
repository and are not committed here.

Run `scripts/fetch_inputs.sh` on a host with Git LFS to reconstruct and verify
the ignored input tree from these public sources.
