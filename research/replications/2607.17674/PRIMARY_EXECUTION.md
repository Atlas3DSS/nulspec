# Primary execution record

## Track R Qwen2.5-0.5B completed attempt `20260802T032037Z-e7fbc95614b1`

This exact registered released-code arm started at
`2026-08-02T03:20:37.131451Z` and completed with exit code 0 at
`2026-08-02T09:33:05.260934Z` on the RTX PRO 6000. Its accelerator wall-clock
interval was 22,348.129 seconds (6 hours, 12 minutes, 28.129 seconds). The
repository was clean at commit
`e7fbc95614b1ff6afab2d4560a43c20da724e197` at both boundaries, and the pinned
upstream tree retained revision `0c0f221d7dc37cd4eb7fb1af3332520bccf4d9fe`
with only registered generated cache paths present.

The base model completed 782 steps with best validation loss 0.212769. Its
sampled test response accuracy was 0.9662 and its mean final linear-probe
accuracy across 65 positions was 0.794148. The factorization then completed all
782 batches with best validation loss 0.909370 and test total loss 0.901685. The
unchanged standalone evaluator returned:

| Metric | Observed | Digitized Figure 3 | Absolute difference | Within 0.03 |
|---|---:|---:|---:|:---:|
| Distributional Fidelity | 0.9928 | 0.995 | 0.0022 | yes |
| Analogical Consistency | 0.326171875 | 0.91 | 0.583828125 | no |

Thus the first released-code arm closely reproduces the digitized fidelity bar
but not the reported analogical-consistency bar. It is not a close numerical
reproduction overall. The paper-level result remains deferred until the second
released-code arm completes, and the headline comparison against other
objectives remains untestable from the public v1 configuration matrix. The
released evaluator retains only aggregate outcomes, so the preregistered
within-evaluation interval is unavailable; fresh-training and fresh-decoding
variance are also unidentified.

The base-model post-run inventory exactly reproduces the preregistered input
manifest SHA-256
`07b3639f317b167aa48b2e499b2af56b06c0f9ca83ed819789c111c52921c8d6`
(19 files, 8,656,847,364 bytes). The separate environment supplement records
57 packages, the frozen `uv.lock`, and package-list SHA-256
`b2e50a58b2e785e4dba2202d2a823a6528fdd8daa5b962f5007db22b2ca56099`;
its file SHA-256 is
`0bd418d1ff6f72ffd46791a9776c16f33f00d75c66f8dc97485776582c48cddf`.
The complete 40-file, 23,997,999,538-byte attempt inventory has SHA-256
`5e7d6e7080348d598588e9d6515718d8ae066688775ea993ec3e68fd8c11b6dd`.
The immutable start, completion, factorization-metric, and evaluation-metric
hashes are respectively
`74cd714c3ce7c811585f2346419b244f4f07b15f97b3399d82001dee0685ae61`,
`bbd9b89da7357e2734c15b484296f4aa59e866f8296ffa282af02cb34405debc`,
`0a7de9722119e22c57c76a0e6b72ef33dba65d3e188c0606c421cd610fb5eee9`,
and
`6ac5e6a153f37d70df15c988e14f8bce93cffb9b6234b624a93ab1cfa0d0e6eb`.

One local thermal-control mapping error briefly reduced GPU clocks during the
final evaluator. It produced no Xid, CUDA error, process interruption, source
change, or memory-pressure event; correcting the UUID-to-fan mapping returned
the card below 80 C under full load. The result remains an eligible unchanged-
code primary observation, while its wall-clock includes that slowdown and the
error remains disclosed as LRS-LOCAL-064.

The first post-run analyzer snapshot records one completed arm and three
pending arms. Its JSON and Markdown SHA-256 values are respectively
`af3df1463cfdd8b673d49cf4e30d28db4e368527195bcbd1a88df2544eaf88d4`
and
`fe5e06215998f3a104db718193c769f2ba20bfa78efe94e2c719d5b49f4b2723`.

## Track R Qwen2.5-1.5B recovered evaluation `20260802T093929Z-e506ae76f6ca`

This exact registered released-code arm began at
`2026-08-02T09:39:29.933519Z` on the RTX PRO 6000. Factorization completed all
782 batches, wrote its normal checkpoints and metrics, and finished its final
test evaluation at `2026-08-02T19:08:54Z`. The factorization's best validation
loss was 0.070696, its test total loss was 0.075813, and its sampled-test
Distributional Fidelity was 0.9750.

The outer runner then ended at `2026-08-02T19:09:05.441378Z` with exit code
141, 34,175.508 seconds (9 hours, 29 minutes, 35.508 seconds) after its start.
The failure was an observer-output transport SIGPIPE, not a CUDA, training,
checkpoint, or metric failure. It occurred before the standalone evaluator
could run. The failed boundary remains immutable and is not relabeled as an
ordinary completion.

Recovery runtime v1.0.2 started a separately labeled attempt at
`2026-08-02T20:24:48.643241Z`. It verified the failed manifest, factorization
configuration and metric hashes, exact `epoch-0001.pt` checkpoint hash,
evaluation config, evaluator source, repository state, and upstream revision.
It then ran only the unchanged released standalone evaluator with the original
command semantics. The recovery completed at
`2026-08-02T21:10:49.856951Z`, an accelerator wall-clock interval of 2,761.214
seconds (46 minutes, 1.214 seconds), with exit code 0 and no scientific change.

The recovered standalone evaluator returned:

| Metric | Observed | Digitized Figure 3 | Absolute difference | Within 0.03 |
|---|---:|---:|---:|:---:|
| Distributional Fidelity | 0.9754 | 0.995 | 0.0196 | yes |
| Analogical Consistency | 0.82421875 | 0.91 | 0.08578125 | no |

The 1.5B arm therefore supports the registered direction because both metrics
exceed 0.95 and 0.80 respectively, but it is not a close numerical reproduction
because Analogical Consistency is outside tolerance. Together, the two Track R
arms closely reproduce fidelity but not analogical consistency: the 0.5B miss
is large and the 1.5B miss is smaller but still material under the frozen rule.
The aggregate analyzer labels released global+token evidence `mixed` and keeps
the paper's broader objective comparison untestable from the public v1 matrix.

The immutable original start and failed-boundary SHA-256 values are
`3bd673e0fd29bb957c9b96a6478556586909d853fc1aaaaa82141482bda31738`
and
`ad42225ff31b341779f3e6c6affd577b2a82d39a89e0a097459325881ee4fb82`.
The factorization metrics and recovery source-binding hashes are
`b3d5f466bd97f8462061972d3839fc7ec747f13873a8c0f541b05175a6b15aa3`
and
`57858ed28b2f33bd7539e3ab2c300cbc66b0c879c4db579d882d29bf1d0eb506`.
The recovery start, recovery completion, evaluation metrics, and evaluation
file-manifest hashes are respectively
`23ad0bd8b4028865be7c24cedcdd7757f3d13f14d82f794452dc1f40be56c1ab`,
`a688aa1a722cbbc87f6a44ff8cc5653d89e1418786bccec593e63490bc61a2ca`,
`246b27e57e91b4bce37862edc95d0b7e6a2e1ae095a0082e4d0fcfc0c7a210ed`,
and
`98a1a9c141565a80a8f733c4637c1d2dd684e879481afb94cc14819901dd0022`.

The corrected append-only matrix snapshot contains one ordinary completion,
one recovered evaluation, and two pending manuscript-method arms, with no
invalid terminal records. Its JSON and Markdown SHA-256 values are
`425fbf209a21ac2d168761e3ed512ef4327b2e757a1a415f4b5b0f9bfde5d7a8`
and
`3f65f1aec83d4a1e9dfbfa90d2065373e9c1b9ea707d095e3d09d892ecf782ad`.

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
