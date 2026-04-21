#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
TMP_FILE="${ROOT_DIR}/../../src/.tmp_devcontainer_smoke"

pass() { echo "[PASS] $1"; }
fail() { echo "[FAIL] $1" >&2; exit 1; }

cd "${ROOT_DIR}"

echo "Running devcontainer-smoke-test..."

# Ensure dummy dev service is available independently.
docker compose up -d dev >/dev/null

# 1) Mount visible
if ./scripts/dev-cmd.sh /bin/sh -lc "test -d /workspace/src"; then
  pass "mount visible"
else
  fail "mount not visible"
fi

# 1b) Python base installation available
if ./scripts/dev-cmd.sh python3 --version >/dev/null; then
  pass "python base install"
else
  fail "python base install"
fi

# 2) Env roundtrip (explicit passthrough)
if [ "$(./scripts/dev-cmd.sh -e CURSOR_SMOKE=ok /bin/sh -lc 'echo ${CURSOR_SMOKE:-}')" = "ok" ]; then
  pass "env roundtrip"
else
  fail "env roundtrip"
fi

# 3) Exitcode passthrough
if ./scripts/dev-cmd.sh /bin/sh -lc "exit 17"; then
  fail "exitcode passthrough"
else
  rc=$?
  [ "${rc}" -eq 17 ] && pass "exitcode passthrough" || fail "exitcode passthrough (got ${rc})"
fi

# 4) Session open/close (non-interactive mode)
if [ "$(./scripts/dev-session.sh --cmd 'echo session_ok')" = "session_ok" ]; then
  pass "session open/close"
else
  fail "session open/close"
fi

# 5) Filesystem operation in mounted source
./scripts/dev-cmd.sh /bin/sh -lc "echo smoke > /workspace/src/.tmp_devcontainer_smoke"
if ./scripts/dev-cmd.sh /bin/sh -lc "test -f /workspace/src/.tmp_devcontainer_smoke"; then
  pass "filesystem create"
else
  fail "filesystem create"
fi
./scripts/dev-cmd.sh /bin/sh -lc "rm -f /workspace/src/.tmp_devcontainer_smoke"
if [ ! -f "${TMP_FILE}" ]; then
  pass "filesystem rm"
else
  fail "filesystem rm"
fi

# 6) Policy header present
policy_out="$(./scripts/dev-cmd.sh /bin/sh -lc "echo header_check" 2>&1 || true)"
if printf '%s\n' "${policy_out}" | grep -q "policy_header mode=dev-cmd backend=compose service=dev"; then
  pass "policy header"
else
  fail "policy header"
fi

echo "devcontainer-smoke-test completed."
