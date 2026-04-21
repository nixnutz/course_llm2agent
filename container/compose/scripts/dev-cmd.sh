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

if [ $# -eq 0 ]; then
  echo "Usage: $0 [-e KEY=VALUE ...] <command> [args...]" >&2
  exit 2
fi

env_args=()
while [ $# -gt 0 ]; do
  case "$1" in
    -e|--env)
      if [ $# -lt 2 ]; then
        echo "Missing value after $1" >&2
        exit 2
      fi
      env_args+=("-e" "$2")
      shift 2
      ;;
    --)
      shift
      break
      ;;
    *)
      break
      ;;
  esac
done

if [ $# -eq 0 ]; then
  echo "No command provided for dev-cmd." >&2
  exit 2
fi

echo "policy_header mode=dev-cmd backend=${backend} service=${service}" >&2

docker compose exec -T "${env_args[@]}" -w "${workdir}" "${service}" "$@"
