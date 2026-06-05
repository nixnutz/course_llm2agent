#!/usr/bin/env bash
set -euo pipefail
# Purpose: reset all toxics and re-enable all proxies.
# Called by: Make targets and pytest teardown helpers.

# Host-side default (make/localhost). Dev container must set TOXIPROXY_URL from .env (http://toxiproxy:8474).
TOXIPROXY_URL="${TOXIPROXY_URL:-http://localhost:8474}"

curl -fsS -X POST "${TOXIPROXY_URL}/reset" >/dev/null
echo "Toxiproxy reset complete"
