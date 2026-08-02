# Primary execution record

## Track M Qwen2.5-0.5B attempt `20260802T073134Z-382f3d5046a0`

This exact registered manuscript-method arm started at
`2026-08-02T07:31:34.872727Z` on an RTX 4090 and ended with exit code 1 at
`2026-08-02T08:38:38.973348Z`. Its accelerator wall-clock interval was
4,024.101 seconds (1 hour, 7 minutes, 4.101 seconds). The repository was clean
at commit `382f3d5046a0b41607a4e9e2e84545f5b2f3ab45` at both boundaries, and
the upstream tree retained revision
`0c0f221d7dc37cd4eb7fb1af3332520bccf4d9fe` with only the registered generated
path classes present.

The arm reused the frozen Track R base-model input identified by manifest
SHA-256 `07b3639f317b167aa48b2e499b2af56b06c0f9ca83ed819789c111c52921c8d6`.
It successfully generated all 100,000 training, 10,000 validation, and 10,000
test responses from that base model under the released sampling implementation.
The upstream sample manifest reports 3,970.677 seconds for generation. The
three Parquet SHA-256 values are:

| Split | Rows | SHA-256 |
|---|---:|---|
| train | 100,000 | `405cde2578bb7adb7ae55ee4be571632023f3237fb04ebbf3eb7fff9b63a4c87` |
| validation | 10,000 | `2c553b6340bf3aa427c7abf21772609af1ba41fe0eca25db2c37660b804d4445` |
| test | 10,000 | `b9418e77c5ee35e6037de7cf4209312d09caf775465eec91d5a8da88accf144a` |

After loading the factorization backbones and resizing the frozen base-model
reference embeddings to vocabulary size 151,672, the unchanged code raised
`torch.AcceleratorError: CUDA error: out of memory` while estimating
`c_theta`. The immediate operation was the attention-mask transfer in
`_compute_base_model_y_region_validation_loss`, called by
`_estimate_c_theta`. System RAM remained ample and the process released the GPU
normally after its terminal manifest was written; this was a device-memory
limit on the 24 GB execution card, not a host-memory guard trip.

No factorization optimizer step or standalone evaluation completed. This
attempt therefore provides no Distributional Fidelity, Analogical Consistency,
or scientific evidence for or against the paper. It will not be resumed,
overwritten, or silently treated as a smaller configuration. A retry must be a
fresh registered attempt on the 96 GB card and must preserve the released
configuration.

The immutable `run.start.json` and `run.failed.json` hashes are respectively
`61d9c75cefffdb63f798b3a6d742c779a17a9a53c8405058fcd2085248cebba6`
and
`1e8c1babaef9e41cff65ed040ade1114f8af7aa045d0099fc5a37acaf6ac30e7`.
A post-run manifest covers 12 retained files and 9,889,437 bytes; its own
SHA-256 is
`8daaa3d800fb06aea10ca837a40dd83315f86a23b7770179ac7a1f439adccdf1`.
The separately labeled package supplement records 57 packages, the frozen
`uv.lock` hash, and package-list SHA-256
`b2e50a58b2e785e4dba2202d2a823a6528fdd8daa5b962f5007db22b2ca56099`;
the supplement file SHA-256 is
`b215fbced71906f642890e0d9dd8cf7ad567ed32f79d5132ca71f1b9f57d1b6f`.

The first post-run analyzer snapshot records this arm as `failed` and defers
every paper-level verdict. Its JSON and Markdown hashes are respectively
`9c7eb64d57f3aa43eaac00cb97227efab6da2b1a6a236b09be8342ef625aa2eb`
and
`3659e93e21e509d76ebf0bff795173513ebf44e082586fc208853b929f1eaa22`.
