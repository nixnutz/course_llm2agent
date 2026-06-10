#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/load-container-env.sh
source "${SCRIPT_DIR}/lib/load-container-env.sh"

: "${SBASH_EXEC_IMAGE_NAME:?Missing required environment variable: SBASH_EXEC_IMAGE_NAME}"
docker image inspect "${SBASH_EXEC_IMAGE_NAME}" >/dev/null
