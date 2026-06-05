#!/usr/bin/env bash
set -euo pipefail
# Purpose: add/remove toxics on a named Toxiproxy proxy.
# Called by: Make targets and manual local chaos runs.
# Notes: supports deterministic test setup from host/dev workflows.

# Host-side default (make/localhost). Dev container must set TOXIPROXY_URL from .env (http://toxiproxy:8474).
TOXIPROXY_URL="${TOXIPROXY_URL:-http://localhost:8474}"
MODE="${1:-}"

usage() {
  echo "Usage:"
  echo "  $0 add <proxy> <toxic_name> <type> [json_attrs] [stream] [toxicity]"
  echo "  $0 remove <proxy> <toxic_name>"
  exit 2
}

if [ -z "${MODE}" ]; then
  usage
fi

case "${MODE}" in
  add)
    proxy="${2:-}"
    toxic_name="${3:-}"
    toxic_type="${4:-}"
    json_attrs="${5:-{}}"
    stream="${6:-downstream}"
    toxicity="${7:-1.0}"
    if [ -z "${proxy}" ] || [ -z "${toxic_name}" ] || [ -z "${toxic_type}" ]; then
      usage
    fi
    curl -fsS -X POST "${TOXIPROXY_URL}/proxies/${proxy}/toxics" \
      -H "Content-Type: application/json" \
      -d "$(cat <<EOF
{
  "name": "${toxic_name}",
  "type": "${toxic_type}",
  "stream": "${stream}",
  "toxicity": ${toxicity},
  "attributes": ${json_attrs}
}
EOF
)" >/dev/null
    echo "Added toxic '${toxic_name}' on proxy '${proxy}'"
    ;;
  remove)
    proxy="${2:-}"
    toxic_name="${3:-}"
    if [ -z "${proxy}" ] || [ -z "${toxic_name}" ]; then
      usage
    fi
    curl -fsS -X DELETE "${TOXIPROXY_URL}/proxies/${proxy}/toxics/${toxic_name}" >/dev/null
    echo "Removed toxic '${toxic_name}' from proxy '${proxy}'"
    ;;
  *)
    usage
    ;;
esac
