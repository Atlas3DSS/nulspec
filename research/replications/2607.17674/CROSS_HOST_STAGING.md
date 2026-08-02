# Cross-host primary-artifact staging

**Verified:** 2026-08-02T05:27:09Z

To use the separately guarded RTX 4090 host without violating the frozen
one-experimental-workload-per-host rule, the completed base stage from
`R-qwen2.5-0.5b-global-token-b0.01-warmup-s314159`, attempt
`attempt-20260802T032037Z-e7fbc95614b1`, was copied together with its pinned
0.5B model snapshot and immutable benchmark data.

The source base stage already contained `base.complete.json`; the active Track
R factorization did not write to that directory. Transfer used low CPU and I/O
priority with a 30 MB/s bandwidth ceiling. It copied:

- benchmark data: 20,901,783 bytes;
- pinned Qwen2.5-0.5B snapshot: 999,603,933 bytes;
- completed trained base-model tree: 6,468,976,896 bytes.

After transfer, a fresh recursive rsync checksum-only dry run (`-acni`) was
performed independently for all three trees. It exited successfully and
reported no differing file. No partial source, live factorization output, host
credential, or unrelated service state was copied.

The destination Track M runner additionally hashes every base-model input file
under harness tag `2607.17674-primary-harness-v1.0.1`. Its manifest becomes the
authoritative input binding for the new arm; this staging record explains only
how those bytes reached the second host.
