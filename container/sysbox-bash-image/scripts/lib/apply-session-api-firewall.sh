#!/usr/bin/env bash
# Block inner docker0 sources from reaching the Sandbox HTTP API port.
# Sourced from run-api.sh before uvicorn — any exit here keeps the HTTP API down.
set -euo pipefail

: "${SBASH_PORT:?Missing required environment variable: SBASH_PORT}"

if ! command -v iptables >/dev/null 2>&1; then
  echo "apply-session-api-firewall: iptables not available" >&2
  exit 1
fi

_docker0_cidr() {
  local cidr
  cidr="$(ip -4 route show dev docker0 2>/dev/null | awk '/proto kernel/ {print $1; exit}')"
  if [ -n "${cidr}" ]; then
    echo "${cidr}"
    return 0
  fi
  ip -4 addr show dev docker0 2>/dev/null | awk '/inet / {print $2; exit}'
}

_wait_for_docker0_cidr() {
  local attempt max_attempts delay cidr
  max_attempts=30
  delay=1

  for attempt in $(seq 1 "${max_attempts}"); do
    cidr="$(_docker0_cidr)"
    if [ -n "${cidr}" ]; then
      echo "${cidr}"
      return 0
    fi
    if [ "${attempt}" -lt "${max_attempts}" ]; then
      echo "apply-session-api-firewall: docker0 CIDR not ready (${attempt}/${max_attempts}), retrying in ${delay}s..." >&2
      sleep "${delay}"
    fi
  done

  return 1
}

cidr="$(_wait_for_docker0_cidr)" || {
  echo "apply-session-api-firewall: could not resolve docker0 CIDR after retries" >&2
  exit 1
}

_rule_spec=(INPUT -s "${cidr}" -p tcp --dport "${SBASH_PORT}" -j DROP)

if iptables -C "${_rule_spec[@]}" 2>/dev/null; then
  echo "apply-session-api-firewall: rule already present for ${cidr} -> tcp:${SBASH_PORT}"
else
  iptables -I "${_rule_spec[@]}"
  if ! iptables -C "${_rule_spec[@]}" 2>/dev/null; then
    echo "apply-session-api-firewall: rule insert failed verification (iptables INPUT DROP missing)" >&2
    exit 1
  fi
  echo "apply-session-api-firewall: DROP ${cidr} -> tcp:${SBASH_PORT}"
fi
