#!/usr/bin/env bash
# Export selected Compose env vars from PID 1 (systemd) into systemd service scripts.
set -euo pipefail

_load_env_key() {
  local key="$1"
  local value
  value="$(tr '\0' '\n' </proc/1/environ | sed -n "s/^${key}=//p" | head -n1)"
  if [ -n "${value}" ]; then
    export "${key}=${value}"
  fi
}

for key in \
  SBASH_PORT \
  SBASH_SESSION_NETWORK_NAME \
  SBASH_BIND_HOST \
  SBASH_EXEC_IMAGE_NAME \
  SBASH_EXEC_IMAGE_ARCHIVE \
  SBASH_SESSIONS_ROOT \
  SBASH_MAX_SCRIPT_BYTES \
  SBASH_MAX_STDOUT_BYTES \
  SBASH_MAX_STDERR_BYTES \
  SBASH_DEFAULT_TIMEOUT_SECONDS; do
  _load_env_key "${key}"
done
