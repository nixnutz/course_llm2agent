#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="${DEV_WRAPPER_CONFIG:-dev-wrapper.yaml}"

cfg() {
  local key="$1"
  awk -F': *' -v k="$key" '$1 == k {print $2}' "${CONFIG_FILE}" | sed 's/[[:space:]]*$//' | head -n1
}

if [ ! -f "${CONFIG_FILE}" ]; then
  echo "Missing wrapper config: ${CONFIG_FILE}" >&2
  exit 1
fi

backend="$(cfg backend)"
service="$(cfg service)"
workdir="$(cfg workdir)"

if [ "${backend}" != "compose" ]; then
  echo "Unsupported backend in ${CONFIG_FILE}: ${backend}" >&2
  exit 1
fi

if [ "${1:-}" = "--cmd" ]; then
  shift
  if [ $# -eq 0 ]; then
    echo "Usage: $0 --cmd '<shell command>'" >&2
    exit 2
  fi
  echo "policy_header mode=dev-session backend=${backend} service=${service}" >&2
  docker compose exec -T -w "${workdir}" "${service}" /bin/sh -lc "$*"
  exit 0
fi

echo "policy_header mode=dev-session backend=${backend} service=${service}" >&2
docker compose exec -it -w "${workdir}" "${service}" /bin/sh
