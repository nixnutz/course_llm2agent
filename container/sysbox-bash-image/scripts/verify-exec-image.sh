#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/load-container-env.sh
source "${SCRIPT_DIR}/lib/load-container-env.sh"

name="${SBASH_EXEC_IMAGE_NAME:-course-llm-sysbox-bash-exec:dev}"
docker image inspect "${name}" >/dev/null
