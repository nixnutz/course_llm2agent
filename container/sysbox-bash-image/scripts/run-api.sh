#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/load-container-env.sh
source "${SCRIPT_DIR}/lib/load-container-env.sh"
# shellcheck source=lib/resolve-bind-host.sh
source "${SCRIPT_DIR}/lib/resolve-bind-host.sh"
# shellcheck source=lib/ensure-session-network.sh
source "${SCRIPT_DIR}/lib/ensure-session-network.sh"
# shellcheck source=lib/apply-session-network-firewall.sh
source "${SCRIPT_DIR}/lib/apply-session-network-firewall.sh"

cd /opt/sysbox-bash-app
: "${SBASH_PORT:?Missing required environment variable: SBASH_PORT}"
exec /opt/sysbox-bash-venv/bin/uvicorn main:app --host "${SBASH_BIND_HOST}" --port "${SBASH_PORT}"
