#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/load-container-env.sh
source "${SCRIPT_DIR}/lib/load-container-env.sh"

: "${SBASH_EXEC_IMAGE_ARCHIVE:?Missing required environment variable: SBASH_EXEC_IMAGE_ARCHIVE}"
: "${SBASH_EXEC_IMAGE_NAME:?Missing required environment variable: SBASH_EXEC_IMAGE_NAME}"
archive="${SBASH_EXEC_IMAGE_ARCHIVE}"
name="${SBASH_EXEC_IMAGE_NAME}"

waited=0
until docker info >/dev/null 2>&1; do
  if [ "${waited}" -ge 60 ]; then
    echo "ERROR: inner Docker not ready after 60s" >&2
    exit 1
  fi
  sleep 1
  waited=$((waited + 1))
done

if docker image inspect "${name}" >/dev/null 2>&1; then
  echo "Exec image ${name} already present; skipping docker load."
  exit 0
fi

if [ ! -s "${archive}" ]; then
  echo "ERROR: exec image archive missing or empty: ${archive}" >&2
  exit 1
fi

docker load -i "${archive}"
"${SCRIPT_DIR}/verify-exec-image.sh"
