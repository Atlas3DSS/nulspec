#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${UPSTREAM_ROOT:-$WORKSPACE/paper_repro/SLM-RL-Agents}"
REPOSITORY="https://github.com/rezwanh001/SLM-RL-Agents.git"
REVISION="64acb621037c711395f2d77516bee70d8a49b819"
PATCH_FILE="$WORKSPACE/patches/2607.25091/reproduction.patch"

if [[ -e "$TARGET" && ! -d "$TARGET/.git" ]]; then
  echo "target exists but is not a Git checkout: $TARGET" >&2
  exit 2
fi

if [[ ! -d "$TARGET/.git" ]]; then
  git clone "$REPOSITORY" "$TARGET"
fi

actual_revision="$(git -C "$TARGET" rev-parse HEAD)"
if [[ "$actual_revision" != "$REVISION" ]]; then
  if [[ -n "$(git -C "$TARGET" status --porcelain)" ]]; then
    echo "upstream checkout is dirty; refusing to change revision" >&2
    exit 2
  fi
  git -C "$TARGET" fetch origin "$REVISION"
  git -C "$TARGET" checkout --detach "$REVISION"
fi

if git -C "$TARGET" apply --reverse --check "$PATCH_FILE" >/dev/null 2>&1; then
  echo "reproduction patch is already applied"
elif git -C "$TARGET" apply --check "$PATCH_FILE" >/dev/null 2>&1; then
  git -C "$TARGET" apply "$PATCH_FILE"
  echo "applied reproduction patch"
else
  echo "checkout does not match either clean or patched expected state" >&2
  git -C "$TARGET" status --short >&2
  exit 2
fi

git -C "$TARGET" rev-parse HEAD
git -C "$TARGET" status --short
