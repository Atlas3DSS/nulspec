#!/usr/bin/env bash
# Fetch and checksum the exact public paper, code, data, and released artifacts.

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
STUDY_DIR=$(cd -- "$SCRIPT_DIR/.." && pwd)
WORK_DIR="$STUDY_DIR/work"
SOURCE_DIR="$WORK_DIR/source"
UPSTREAM_DIR="$WORK_DIR/upstream"
UPSTREAM_URL=https://github.com/thetechdude124/SADDLE-POINT-RECRUITMENT-FOR-KNOWLEDGE-DISTILLATION.git
UPSTREAM_COMMIT=7f1655ff1295c9a6dcf8d24f6410a036cd7e3497

command -v curl >/dev/null
command -v git >/dev/null
git lfs version >/dev/null
mkdir -p "$SOURCE_DIR"

curl --fail --location --retry 3 \
    https://arxiv.org/abs/2607.23346v1 \
    --output "$SOURCE_DIR/arxiv-abs.html"
curl --fail --location --retry 3 \
    https://arxiv.org/pdf/2607.23346v1 \
    --output "$SOURCE_DIR/arxiv-paper.pdf"
curl --fail --location --retry 3 \
    https://export.arxiv.org/e-print/2607.23346v1 \
    --output "$SOURCE_DIR/arxiv-source.tar"

if [[ ! -d "$UPSTREAM_DIR/.git" ]]; then
    GIT_LFS_SKIP_SMUDGE=1 git clone --filter=blob:none "$UPSTREAM_URL" "$UPSTREAM_DIR"
fi
test "$(git -C "$UPSTREAM_DIR" remote get-url origin)" = "$UPSTREAM_URL"
git -C "$UPSTREAM_DIR" fetch origin "$UPSTREAM_COMMIT"
git -C "$UPSTREAM_DIR" checkout --detach "$UPSTREAM_COMMIT"
test "$(git -C "$UPSTREAM_DIR" rev-parse HEAD)" = "$UPSTREAM_COMMIT"

git -C "$UPSTREAM_DIR" lfs pull --include="TESTSET.pth,MODELS/SPRKD_MALARIA.pth,MODELS/CONTROL_MALARIA.pth,MODELS/RKD_MALARIA_STUDENT.pth,TRUE_MALARIA_ENSEMBLE_TEACHER_SADDLE_POINTS.pth,TRUE_TEACHER_1_MALARIA.pth,METRICS/HESSIAN EIGENSPECTRA/EIGS_500_SPRKD_MALARIA.pth,METRICS/HESSIAN EIGENSPECTRA/EIGS_500_CONTROL_MALARIA.pth,METRICS/HESSIAN EIGENSPECTRA/EIGS_RKD_MALARIA_STUDENT.pth"

(
    cd "$STUDY_DIR"
    sha256sum --check <<'CHECKSUMS'
d60aee39d19341cf642d889540558cd80168f97d1877881f88cf9fc04b6afd29  work/source/arxiv-abs.html
f9ad5d1a4a12a930d0fd94913b2c4b28b738f203ad9b28fb58599a900e07a8db  work/source/arxiv-paper.pdf
b7f25d66b8b4947f609951bc1a424a0cfcb2d5cc0c2e5de59c94b27c3dffa6dd  work/source/arxiv-source.tar
f8f19a260a564b258cda59d29c744151cf6f1afb808df2f80456371fa393d08e  work/upstream/TESTSET.pth
cf218a350c4cd81661ba3efe517b096beeb72b38647ec80973706789ac75314d  work/upstream/MODELS/SPRKD_MALARIA.pth
b79eb99815065401c2f66b3c54fecff44ecf1136b96897ede6df792e73da7aff  work/upstream/MODELS/CONTROL_MALARIA.pth
8a2368c288e021865dbc5b50a541eccd87b4f949be36b9837f61ab65d95f08b4  work/upstream/MODELS/RKD_MALARIA_STUDENT.pth
adbb032696c9572bb10ab9c097965d6c38906ecb151ebe3fda7c5ba07250a1ee  work/upstream/TRUE_MALARIA_ENSEMBLE_TEACHER_SADDLE_POINTS.pth
0e492e6d8c6e74b33476804120a7e9a30c10ed2e78636e3b55e1b484c19560f7  work/upstream/TRUE_TEACHER_1_MALARIA.pth
68b13de8f32ba74460e4eb4bdf414995b28bf099aecbc758b3e87bda0ca8f443  work/upstream/METRICS/LOSSES AND ACCURACIES/500_SPRKD_LOSSES.pkl
5b8dec1d73b4ca9db4594a59c5643bdd2ed7857bb594cbf75025628671bf6ae8  work/upstream/METRICS/LOSSES AND ACCURACIES/500_CONTROL_STUDENT_LOSSES.pkl
7dd822d18a2b5f96981810826f16db65378d206608bd58a6afce05838eb61014  work/upstream/METRICS/LOSSES AND ACCURACIES/RKD_STUDENT_METRICS.pkl
76de32cb1b004f0bed54c62b74be23de85c9dd71eae57f93bd1fd61cec6cdb8b  work/upstream/METRICS/HESSIAN EIGENSPECTRA/EIGS_500_SPRKD_MALARIA.pth
2f2fb29813c216ebb7954b8d2c239d6501dd81a1349dd7d70e82e0f51eb2e425  work/upstream/METRICS/HESSIAN EIGENSPECTRA/EIGS_500_CONTROL_MALARIA.pth
9d3f8d813f85fb96b56157b3e13bb5e58c10961802ce424826c64ba629736808  work/upstream/METRICS/HESSIAN EIGENSPECTRA/EIGS_RKD_MALARIA_STUDENT.pth
CHECKSUMS
)

DATASET_DIGEST=$(
    cd "$UPSTREAM_DIR/cell_images"
    find . -type f -name '*.png' -print0 \
        | sort -z \
        | xargs -0 sha256sum \
        | sha256sum \
        | cut -d' ' -f1
)
EXPECTED_DATASET_DIGEST=4fc7205c482dd43959cf1795ccbdbc0f819c1001dca374a0ee14eb9a3d5c1381
test "$DATASET_DIGEST" = "$EXPECTED_DATASET_DIGEST"
test "$(find "$UPSTREAM_DIR/cell_images" -type f -name '*.png' | wc -l)" -eq 27558

printf 'All SPRKD inputs match the frozen manifest.\n'
