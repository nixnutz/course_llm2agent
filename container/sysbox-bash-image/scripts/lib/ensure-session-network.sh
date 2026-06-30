#!/usr/bin/env bash
# Ensure the dedicated inner session bridge exists with ICC disabled.
# Sourced from run-api.sh before firewall + uvicorn — any exit keeps the HTTP API down.
set -euo pipefail

SBASH_SESSION_NETWORK_NAME="${SBASH_SESSION_NETWORK_NAME:-sbash_sessions}"
MANAGED_LABEL="course.llm2agent.sysbox_bash.managed=true"

if ! command -v docker >/dev/null 2>&1; then
  echo "ensure-session-network: docker not available" >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "ensure-session-network: inner Docker is not ready" >&2
  exit 1
fi

_icc_enabled() {
  docker network inspect "${SBASH_SESSION_NETWORK_NAME}" \
    --format '{{index .Options "com.docker.network.bridge.enable_icc"}}' 2>/dev/null
}

if docker network inspect "${SBASH_SESSION_NETWORK_NAME}" >/dev/null 2>&1; then
  icc="$(_icc_enabled)"
  if [ "${icc}" != "false" ]; then
    echo "ensure-session-network: network ${SBASH_SESSION_NETWORK_NAME} exists but ICC is not disabled (enable_icc=${icc:-unset})" >&2
    echo "ensure-session-network: remove the misconfigured network with: docker network rm ${SBASH_SESSION_NETWORK_NAME}" >&2
    exit 1
  fi
  echo "ensure-session-network: network ${SBASH_SESSION_NETWORK_NAME} already exists (ICC off)"
else
  docker network create \
    --driver bridge \
    --opt "com.docker.network.bridge.enable_icc=false" \
    --label "${MANAGED_LABEL}" \
    "${SBASH_SESSION_NETWORK_NAME}"
  echo "ensure-session-network: created network ${SBASH_SESSION_NETWORK_NAME} (ICC off)"
fi
