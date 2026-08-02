#!/usr/bin/env bash
set -euo pipefail

DESTINATION="${1:?usage: bootstrap_2607_17674_upstream.sh DESTINATION}"
REVISION="0c0f221d7dc37cd4eb7fb1af3332520bccf4d9fe"
ARCHIVE_SHA256="fea5a7f598b5bbeb810dca9228c8ed1e41b87d8ff48cd2d404bcd53752268c79"

USER_ROOT="$(getent passwd "$(id -u)" | cut -d: -f6)"
if [[ -z "$USER_ROOT" || "$USER_ROOT" != /* ]]; then
  echo "could not resolve the current user's home directory" >&2
  exit 2
fi
if [[ "$DESTINATION" != /* ]]; then
  echo "destination must be an absolute path" >&2
  exit 2
fi
case "$DESTINATION" in
  /|/home|"$USER_ROOT")
    echo "refusing broad destination: $DESTINATION" >&2
    exit 2
    ;;
esac

if [[ -e "$DESTINATION" ]]; then
  if [[ ! -d "$DESTINATION/.git" ]]; then
    echo "existing destination is not a Git checkout: $DESTINATION" >&2
    exit 2
  fi
else
  mkdir -p "$(dirname "$DESTINATION")"
  git clone --filter=blob:none \
    https://github.com/Awni00/latent-strategies-in-lms.git \
    "$DESTINATION"
fi

git -C "$DESTINATION" fetch --no-tags origin "$REVISION"
git -C "$DESTINATION" checkout --detach "$REVISION"

if [[ -n "$(git -C "$DESTINATION" status --porcelain=v1)" ]]; then
  echo "upstream checkout is dirty after bootstrap" >&2
  exit 2
fi

actual_archive_sha256="$(
  git -C "$DESTINATION" archive --format=tar HEAD | sha256sum | awk '{print $1}'
)"
if [[ "$actual_archive_sha256" != "$ARCHIVE_SHA256" ]]; then
  echo "upstream archive digest mismatch" >&2
  exit 2
fi

uv sync --project "$DESTINATION" --frozen
echo "pinned upstream and frozen environment ready: $DESTINATION"
