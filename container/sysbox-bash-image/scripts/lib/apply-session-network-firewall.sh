#!/usr/bin/env bash
# Block session-bridge sources from reaching the sysbox_bash host netns (all ports).
# Sourced from run-api.sh before uvicorn — any exit here keeps the HTTP API down.
set -euo pipefail

SBASH_SESSION_NETWORK_NAME="${SBASH_SESSION_NETWORK_NAME:-sbash_sessions}"

if ! command -v iptables >/dev/null 2>&1; then
  echo "apply-session-network-firewall: iptables not available" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "apply-session-network-firewall: docker not available" >&2
  exit 1
fi

_session_network_cidr() {
  local cidr bridge_name
  cidr="$(docker network inspect "${SBASH_SESSION_NETWORK_NAME}" \
    --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null | head -n1)"
  if [ -n "${cidr}" ]; then
    echo "${cidr}"
    return 0
  fi

  bridge_name="$(docker network inspect "${SBASH_SESSION_NETWORK_NAME}" \
    --format '{{index .Options "com.docker.network.bridge.name"}}' 2>/dev/null)"
  if [ -n "${bridge_name}" ]; then
    cidr="$(ip -4 route show dev "${bridge_name}" 2>/dev/null | awk '/proto kernel/ {print $1; exit}')"
    if [ -n "${cidr}" ]; then
      echo "${cidr}"
      return 0
    fi
    ip -4 addr show dev "${bridge_name}" 2>/dev/null | awk '/inet / {print $2; exit}'
  fi
}

_wait_for_session_network_cidr() {
  local attempt max_attempts delay cidr
  max_attempts=30
  delay=1

  for attempt in $(seq 1 "${max_attempts}"); do
    cidr="$(_session_network_cidr)"
    if [ -n "${cidr}" ]; then
      echo "${cidr}"
      return 0
    fi
    if [ "${attempt}" -lt "${max_attempts}" ]; then
      echo "apply-session-network-firewall: session network CIDR not ready (${attempt}/${max_attempts}), retrying in ${delay}s..." >&2
      sleep "${delay}"
    fi
  done

  return 1
}

_docker0_cidr() {
  local cidr
  cidr="$(ip -4 route show dev docker0 2>/dev/null | awk '/proto kernel/ {print $1; exit}')"
  if [ -n "${cidr}" ]; then
    echo "${cidr}"
    return 0
  fi
  ip -4 addr show dev docker0 2>/dev/null | awk '/inet / {print $2; exit}'
}

_remove_legacy_docker0_port_drop() {
  local docker0_cidr
  docker0_cidr="$(_docker0_cidr)"
  if [ -z "${docker0_cidr}" ] || [ -z "${SBASH_PORT:-}" ]; then
    return 0
  fi

  local _legacy_rule=(INPUT -s "${docker0_cidr}" -p tcp --dport "${SBASH_PORT}" -j DROP)
  if iptables -C "${_legacy_rule[@]}" 2>/dev/null; then
    iptables -D "${_legacy_rule[@]}"
    echo "apply-session-network-firewall: removed legacy docker0 port-specific DROP (${docker0_cidr} -> tcp:${SBASH_PORT})"
  fi
}

cidr="$(_wait_for_session_network_cidr)" || {
  echo "apply-session-network-firewall: could not resolve CIDR for ${SBASH_SESSION_NETWORK_NAME} after retries" >&2
  exit 1
}

_remove_legacy_docker0_port_drop

_rule_spec=(INPUT -s "${cidr}" -j DROP)

if iptables -C "${_rule_spec[@]}" 2>/dev/null; then
  echo "apply-session-network-firewall: rule already present for ${cidr}"
else
  iptables -I "${_rule_spec[@]}"
  if ! iptables -C "${_rule_spec[@]}" 2>/dev/null; then
    echo "apply-session-network-firewall: rule insert failed verification (iptables INPUT DROP missing)" >&2
    exit 1
  fi
  echo "apply-session-network-firewall: DROP ${cidr} (all ports)"
fi
