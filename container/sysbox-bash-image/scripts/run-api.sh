#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/load-container-env.sh
source "${SCRIPT_DIR}/lib/load-container-env.sh"

cd /opt/sysbox-bash-app
port="${SBASH_PORT:-8080}"
exec /opt/sysbox-bash-venv/bin/uvicorn main:app --host 0.0.0.0 --port "${port}"
