#!/usr/bin/env bash
set -euo pipefail
# Purpose: idempotently create required Toxiproxy proxies for local chaos tests.
# Called by: compose one-shot service and Make target.
# Notes: safe to run multiple times; uses /populate with fixed proxy names.

# Host-side default (make/localhost). Dev container must set TOXIPROXY_URL from .env (http://toxiproxy:8474).
TOXIPROXY_URL="${TOXIPROXY_URL:-http://localhost:8474}"
TOXIPROXY_EDGE_LISTEN="${TOXIPROXY_EDGE_LISTEN:-11111}"
TOXIPROXY_OLLAMA_LISTEN="${TOXIPROXY_OLLAMA_LISTEN:-11112}"
LITELLM_INTERNAL_PORT="${LITELLM_INTERNAL_PORT:-4000}"
LITELLM_CHAOS_HOST="${LITELLM_CHAOS_HOST:-litellm_chaos}"
OLLAMA_CONTAINER_PORT="${OLLAMA_CONTAINER_PORT:-11434}"

wait_for_admin() {
  local retries=60
  local i=1
  until curl -fsS "${TOXIPROXY_URL}/version" >/dev/null 2>&1; do
    if [ "${i}" -ge "${retries}" ]; then
      echo "Toxiproxy admin not reachable at ${TOXIPROXY_URL} after ${retries} attempts."
      return 1
    fi
    i=$((i + 1))
    sleep 1
  done
}

wait_for_admin

payload="$(cat <<EOF
[
  {
    "name": "edge_chaos",
    "listen": "0.0.0.0:${TOXIPROXY_EDGE_LISTEN}",
    "upstream": "${LITELLM_CHAOS_HOST}:${LITELLM_INTERNAL_PORT}",
    "enabled": true
  },
  {
    "name": "provider_chaos_ollama",
    "listen": "0.0.0.0:${TOXIPROXY_OLLAMA_LISTEN}",
    "upstream": "ollama:${OLLAMA_CONTAINER_PORT}",
    "enabled": true
  }
]
EOF
)"

curl -fsS -X POST "${TOXIPROXY_URL}/populate" \
  -H "Content-Type: application/json" \
  -d "${payload}" >/dev/null

echo "Toxiproxy proxies ensured: edge_chaos, provider_chaos_ollama"
