#!/usr/bin/env bash
set -euo pipefail
# Purpose: follow all compose logs, then focus on litellm once healthy.
# Called by: `make logs` for startup-to-steady-state log workflow.
# Notes: auto-switches stream to keep operational logs readable.

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT_DIR="$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

LOG_PID=""
cleanup() {
  if [ -n "${LOG_PID}" ] && kill -0 "${LOG_PID}" >/dev/null 2>&1; then
    kill "${LOG_PID}" >/dev/null 2>&1 || true
    wait "${LOG_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

litellm_is_healthy() {
  # docker compose v2 supports JSON formatting; fall back to text grep if unavailable.
  if docker compose ps --help 2>/dev/null | grep -q -- '--format'; then
    docker compose ps --format json \
      | jq -es 'map(select(.Service=="litellm")) | length > 0 and (map(select(.Service=="litellm" and .Health=="healthy")) | length > 0)' >/dev/null 2>&1
  else
    docker compose ps \
      | awk 'BEGIN{found=0;healthy=0} $1=="litellm"{found=1} found==1 && $0 ~ /healthy/{healthy=1} END{exit !(found && healthy)}'
  fi
}

echo "Following all compose service logs until litellm is healthy, then switching to litellm-only logs."
echo "Tip: Ctrl+C stops following."

docker compose logs -f &
LOG_PID="$!"

deadline=$((SECONDS + 900))
while ! litellm_is_healthy; do
  if [ "${SECONDS}" -ge "${deadline}" ]; then
    echo "Timed out waiting for litellm to become healthy; continuing with all-service logs."
    wait "${LOG_PID}"
    exit 0
  fi
  sleep 2
done

echo "litellm is healthy — switching to litellm-only logs."
cleanup
LOG_PID=""

docker compose logs -f --tail=200 litellm
