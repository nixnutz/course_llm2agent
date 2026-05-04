#!/usr/bin/env bash
set -euo pipefail
# Purpose: follow all compose logs, then focus on litellm_clean once healthy.
# Called by: `make logs` for startup-to-steady-state log workflow.
# Notes: auto-switches stream to keep operational logs readable.

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT_DIR="$(CDPATH= cd -- "${SCRIPT_DIR}/../.." && pwd)"
cd "${ROOT_DIR}"

LOG_PID=""
cleanup() {
  if [ -n "${LOG_PID}" ] && kill -0 "${LOG_PID}" >/dev/null 2>&1; then
    kill "${LOG_PID}" >/dev/null 2>&1 || true
    wait "${LOG_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

litellm_clean_is_healthy() {
  # docker compose v2 supports JSON formatting; fall back to text grep if unavailable.
  if docker compose ps --help 2>/dev/null | grep -q -- '--format'; then
    docker compose ps --format json \
      | jq -es 'map(select(.Service=="litellm_clean")) | length > 0 and (map(select(.Service=="litellm_clean" and .Health=="healthy")) | length > 0)' >/dev/null 2>&1
  else
    docker compose ps \
      | awk 'BEGIN{found=0;healthy=0} $1=="litellm_clean"{found=1} found==1 && $0 ~ /healthy/{healthy=1} END{exit !(found && healthy)}'
  fi
}

echo "Following all compose service logs until litellm_clean is healthy, then switching to litellm_clean logs."
echo "Tip: Ctrl+C stops following."

docker compose logs -f &
LOG_PID="$!"

deadline=$((SECONDS + 900))
while ! litellm_clean_is_healthy; do
  if [ "${SECONDS}" -ge "${deadline}" ]; then
    echo "Timed out waiting for litellm_clean to become healthy; continuing with all-service logs."
    wait "${LOG_PID}"
    exit 0
  fi
  sleep 2
done

echo "litellm_clean is healthy — switching to litellm_clean-only logs."
cleanup
LOG_PID=""

docker compose logs -f --tail=200 litellm_clean
