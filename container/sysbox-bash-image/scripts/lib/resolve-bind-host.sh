#!/usr/bin/env bash
# Resolve SBASH_BIND_HOST for uvicorn (Compose backend_core interface).
# Sourced from run-api.sh — exit here prevents uvicorn start (fail-closed with firewall).
set -euo pipefail

_docker0_ipv4() {
  ip -4 addr show dev docker0 2>/dev/null | awk '/inet / {print $2}' | cut -d/ -f1 | head -n1
}

_resolve_bind_ipv4() {
  local host ip
  for host in "$(hostname)" sysbox_bash; do
    ip="$(getent ahostsv4 "${host}" 2>/dev/null | awk '{print $1; exit}')"
    if [ -n "${ip}" ]; then
      echo "${ip}"
      return 0
    fi
  done
  ip -4 addr show dev eth0 2>/dev/null | awk '/inet / {print $2}' | cut -d/ -f1 | head -n1
}

_validate_bind_ip() {
  local bind_ip="$1"
  local docker0_ip

  if [ -z "${bind_ip}" ]; then
    echo "resolve-bind-host: bind IP must not be empty" >&2
    exit 1
  fi
  if [ "${bind_ip}" = "0.0.0.0" ]; then
    echo "resolve-bind-host: bind IP must not be 0.0.0.0" >&2
    exit 1
  fi
  if [ "${bind_ip}" = "127.0.0.1" ]; then
    echo "resolve-bind-host: bind IP must not be 127.0.0.1" >&2
    exit 1
  fi

  docker0_ip="$(_docker0_ipv4)"
  if [ -n "${docker0_ip}" ] && [ "${bind_ip}" = "${docker0_ip}" ]; then
    echo "resolve-bind-host: bind IP must not equal docker0 IP (${docker0_ip})" >&2
    exit 1
  fi
}

if [ -n "${SBASH_BIND_HOST:-}" ]; then
  bind_ip="${SBASH_BIND_HOST}"
  source_label="override"
else
  bind_ip="$(_resolve_bind_ipv4)"
  source_label="auto-detect"
fi

_validate_bind_ip "${bind_ip}"
export SBASH_BIND_HOST="${bind_ip}"
echo "resolve-bind-host: SBASH_BIND_HOST=${SBASH_BIND_HOST} (${source_label})"
