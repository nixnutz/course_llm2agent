#!/usr/bin/env bash
set -euo pipefail
# Purpose: manage reserved local virtual keys and sync them to LiteLLM.
# Called by: Make targets and init wrappers for key lifecycle operations.
# Notes: supports create/overwrite/ensure-file/sync modes via first argument.

MODE="${1:-}"
if [ -z "${MODE}" ]; then
  echo "Usage: $0 <create|overwrite|ensure-file|sync-from-file|sync-init>"
  exit 1
fi

case "${MODE}" in
  create|overwrite|ensure-file|sync-from-file|sync-init) ;;
  *)
    echo "Invalid mode: ${MODE}. Use create, overwrite, ensure-file, sync-from-file, or sync-init."
    exit 1
    ;;
esac

read_env_value() {
  local key="$1"
  if [ ! -f ".env" ]; then
    return 0
  fi
  awk -F= -v k="${key}" '$1==k {sub(/^[[:space:]]+/, "", $2); print $2; exit}' .env
}

LITELLM_PORT="${LITELLM_PORT:-$(read_env_value LITELLM_PORT)}"
MASTER_KEY="${LITELLM_MASTER_KEY:-$(read_env_value LITELLM_MASTER_KEY)}"
LITELLM_HOST="${LITELLM_HOST:-localhost}"
LITELLM_PORT="${LITELLM_PORT:-4000}"
LITELLM_BASE_URL="${LITELLM_BASE_URL:-http://${LITELLM_HOST}:${LITELLM_PORT}}"
KEYS_FILE="${KEYS_FILE:-.state/keys/keys.local.json}"
KEYS_INIT_MODE="${KEYS_INIT_MODE:-required}"

mkdir -p "$(dirname "${KEYS_FILE}")"

if [ -z "${MASTER_KEY}" ]; then
  echo "LITELLM_MASTER_KEY is not set."
  exit 1
fi

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1"
    exit 1
  fi
}

require_cmd curl
require_cmd jq
require_cmd python3

TMP_FILE="$(mktemp)"
trap 'rm -f "${TMP_FILE}" "${TMP_FILE}.next" "${TMP_FILE}.normalized" "${TMP_FILE}.sanitize_report"' EXIT

RESERVED_NAMES=("dev" "stage" "prod" "user1" "user2")

normalize_json() {
  # IMPORTANT: do not use `python3 <<'PY'` here — stdin is consumed by the heredoc and cannot be piped in.
  python3 -c 'import json,sys
payload = sys.stdin.read().strip() or "{}"
data = json.loads(payload)
if isinstance(data, dict) and "keys" in data and isinstance(data["keys"], list):
    normalized = {"keys": []}
    for item in data["keys"]:
        if isinstance(item, dict) and item.get("name") and item.get("token"):
            normalized["keys"].append({"name": str(item["name"]), "token": str(item["token"])})
    print(json.dumps(normalized))
else:
    print(json.dumps({"keys":[]}))
'
}

normalize_and_reserve_json() {
  python3 -c 'import json,sys
allowed = {"dev", "stage", "prod", "user1", "user2"}
payload = sys.stdin.read().strip() or "{}"
data = json.loads(payload)

# Step 1: normalize to {keys:[{name,token}, ...]}
if isinstance(data, dict) and "keys" in data and isinstance(data["keys"], list):
    normalized = {"keys": []}
    for item in data["keys"]:
        if isinstance(item, dict) and item.get("name") and item.get("token"):
            normalized["keys"].append({"name": str(item["name"]), "token": str(item["token"])})
else:
    normalized = {"keys": []}

# Step 2: keep only reserved names (dedupe by name; last wins)
kept = {}
removed = []
for item in normalized["keys"]:
    name = item["name"]
    token = item["token"]
    if name not in allowed:
        removed.append(name)
        continue
    kept[name] = {"name": name, "token": token}

clean = {"keys": [kept[k] for k in sorted(kept.keys())]}
print(json.dumps({"clean": clean, "removed": removed}))
'
}

load_keys_tmp() {
  if [ -f "${KEYS_FILE}" ]; then
    cp "${KEYS_FILE}" "${TMP_FILE}"
  else
    printf '{"keys":[]}\n' > "${TMP_FILE}"
  fi
  cat "${TMP_FILE}" | normalize_json > "${TMP_FILE}.normalized"
  mv "${TMP_FILE}.normalized" "${TMP_FILE}"
}

write_keys_tmp_to_file() {
  mv "${TMP_FILE}" "${KEYS_FILE}"
  # Restore temp file for continued operations.
  cp "${KEYS_FILE}" "${TMP_FILE}"
}

read_existing_token() {
  local name="$1"
  if [ ! -f "${TMP_FILE}" ]; then
    echo ""
    return 0
  fi
  jq -r --arg name "${name}" '.keys[] | select(.name==$name) | .token' "${TMP_FILE}" | sed -n '1p'
}

upsert_key_file() {
  local name="$1"
  local token="$2"
  jq --arg name "${name}" --arg token "${token}" '
    .keys = ((.keys | map(select(.name != $name))) + [{"name": $name, "token": $token}])
  ' "${TMP_FILE}" > "${TMP_FILE}.next"
  mv "${TMP_FILE}.next" "${TMP_FILE}"
}

apply_reserved_sanitization() {
  # NOTE: Never capture this function's output with `$()` — bash runs command substitutions in a subshell,
  # which would discard in-place updates to TMP_FILE.
  local report_file="${TMP_FILE}.sanitize_report"
  cat "${TMP_FILE}" | normalize_and_reserve_json > "${report_file}"

  SANITIZE_REMOVED_ANY=0
  if jq -e '.removed | length > 0' "${report_file}" >/dev/null 2>&1; then
    SANITIZE_REMOVED_ANY=1
    echo "Removed non-reserved virtual key entries from ${KEYS_FILE}: $(jq -r '.removed | join(", ")' "${report_file}")"
  fi

  python3 - <<'PY' "${report_file}" "${TMP_FILE}"
import json, sys

report_path, tmp_path = sys.argv[1], sys.argv[2]
report = json.loads(open(report_path, "r", encoding="utf-8").read())
clean = report.get("clean", {})
if not isinstance(clean, dict):
    clean = {"keys": []}
keys = clean.get("keys", [])
if not isinstance(keys, list):
    keys = []

open(tmp_path, "w", encoding="utf-8").write(json.dumps({"keys": keys}, indent=2) + "\n")
PY
  rm -f "${report_file}"
}

ensure_default_keys_file() {
  local names=("${RESERVED_NAMES[@]}")
  local changed=0
  load_keys_tmp
  apply_reserved_sanitization
  if [ "${SANITIZE_REMOVED_ANY}" = "1" ]; then
    changed=1
  fi
  for name in "${names[@]}"; do
    existing_token="$(read_existing_token "${name}")"
    if [ -n "${existing_token}" ]; then
      continue
    fi
    token="sk-local-${name}-$(python3 - <<'PY'
import secrets
print(secrets.token_hex(16))
PY
)"
    upsert_key_file "${name}" "${token}"
    changed=1
    echo "Added default key entry for ${name}"
  done
  if [ "${changed}" = "1" ] || [ ! -f "${KEYS_FILE}" ]; then
    write_keys_tmp_to_file
    echo "Saved key map to ${KEYS_FILE}"
  fi
}

wait_for_litellm() {
  local retries=60
  local i=1
  until curl -sS "${LITELLM_BASE_URL}/health/readiness" >/dev/null 2>&1; do
    if [ "${i}" -ge "${retries}" ]; then
      echo "LiteLLM is not ready at ${LITELLM_BASE_URL} after ${retries} attempts."
      return 1
    fi
    i=$((i + 1))
    sleep 2
  done
}

delete_remote_key() {
  local token="$1"
  local response
  response="$(curl -sS "${LITELLM_BASE_URL}/key/delete" \
    -H "Authorization: Bearer ${MASTER_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"keys\":[\"${token}\"]}" || true)"
  if ! echo "${response}" | jq -e '.deleted_keys? // empty' >/dev/null 2>&1; then
    curl -sS "${LITELLM_BASE_URL}/key/delete" \
      -H "Authorization: Bearer ${MASTER_KEY}" \
      -H "Content-Type: application/json" \
      -d "{\"key\":\"${token}\"}" >/dev/null || true
  fi
}

upsert_remote_token() {
  local name="$1"
  local token="$2"
  local payload response
  payload="$(jq -cn \
    --arg key_name "${name}" \
    --arg key "${token}" \
    --arg key_alias "${name}" \
    '{
      key_name: $key_name,
      key_alias: $key_alias,
      key: $key,
      metadata: {client: $key_name, environment: "local"},
      models: []
    }')"
  response="$(curl -sS "${LITELLM_BASE_URL}/key/generate" \
    -H "Authorization: Bearer ${MASTER_KEY}" \
    -H "Content-Type: application/json" \
    -d "${payload}")"

  returned_key="$(echo "${response}" | jq -r '.key // empty')"
  if [ -z "${returned_key}" ]; then
    echo "Failed to upsert key ${name}: ${response}"
    return 1
  fi
  if [ "${returned_key}" != "${token}" ]; then
    echo "Warning: LiteLLM returned different token for ${name}; expected file token to be authoritative."
    echo "Response: ${response}"
    return 1
  fi
  echo "Synced token for ${name}"
}

prune_remote_keys_for_reserved_clients() {
  local page=1 total_pages=1
  while [ "${page}" -le "${total_pages}" ]; do
    local resp
    resp="$(curl -sS "${LITELLM_BASE_URL}/key/list?page=${page}&size=50&return_full_object=true" \
      -H "Authorization: Bearer ${MASTER_KEY}")"

    total_pages="$(echo "${resp}" | jq -r '.total_pages // 1')"
    if [ "${total_pages}" -lt 1 ]; then
      total_pages=1
    fi
    local token client
    while IFS=$'\t' read -r token client; do
      [ -n "${token}" ] || continue
      if [ -z "${client}" ] || [ "${client}" = "null" ]; then
        echo "Skipping remote key without metadata.client (token=${token})"
        continue
      fi
      local allowed=0
      for n in "${RESERVED_NAMES[@]}"; do
        if [ "${client}" = "${n}" ]; then
          allowed=1
          break
        fi
      done
      if [ "${allowed}" = "0" ]; then
        echo "Deleting remote key for non-reserved client=${client}"
        delete_remote_key "${token}"
      fi
    done < <(echo "${resp}" | jq -r '.keys[]? | select(type=="object") | [.token, (.metadata.client // "")] | @tsv')

    page=$((page + 1))
  done
}

delete_all_remote_keys_for_client() {
  local client="$1"
  local page=1 total_pages=1
  while [ "${page}" -le "${total_pages}" ]; do
    local resp
    resp="$(curl -sS "${LITELLM_BASE_URL}/key/list?page=${page}&size=50&return_full_object=true" \
      -H "Authorization: Bearer ${MASTER_KEY}")"

    total_pages="$(echo "${resp}" | jq -r '.total_pages // 1')"
    if [ "${total_pages}" -lt 1 ]; then
      total_pages=1
    fi
    local token c
    while IFS=$'\t' read -r token c; do
      [ -n "${token}" ] || continue
      if [ "${c}" = "${client}" ]; then
        delete_remote_key "${token}"
      fi
    done < <(echo "${resp}" | jq -r --arg client "${client}" '.keys[]? | select(type=="object") | [.token, (.metadata.client // "")] | @tsv')

    page=$((page + 1))
  done
}

sync_file_to_remote() {
  load_keys_tmp
  apply_reserved_sanitization
  prune_remote_keys_for_reserved_clients
  count="$(jq '.keys | length' "${TMP_FILE}")"
  if [ "${count}" = "0" ]; then
    echo "No keys in ${KEYS_FILE}; nothing to sync."
    return 0
  fi
  while IFS=$'\t' read -r name token; do
    [ -n "${name}" ] || continue
    delete_all_remote_keys_for_client "${name}"
    upsert_remote_token "${name}" "${token}"
  done < <(jq -r '.keys[] | [.name, .token] | @tsv' "${TMP_FILE}")
}

run_sync_init() {
  case "${KEYS_INIT_MODE}" in
    required|optional|off) ;;
    *)
      echo "Invalid KEYS_INIT_MODE=${KEYS_INIT_MODE}. Allowed values: required, optional, off."
      exit 1
      ;;
  esac

  if [ "${KEYS_INIT_MODE}" = "off" ]; then
    echo "Skipping virtual key init (KEYS_INIT_MODE=off)."
    exit 0
  fi

  ensure_default_keys_file
  if wait_for_litellm && sync_file_to_remote; then
    echo "Virtual key init completed."
    exit 0
  fi

  if [ "${KEYS_INIT_MODE}" = "optional" ]; then
    echo "Virtual key init failed, continuing because KEYS_INIT_MODE=optional."
    exit 0
  fi

  echo "Virtual key init failed (KEYS_INIT_MODE=required)."
  exit 1
}

case "${MODE}" in
  create)
    load_keys_tmp
    apply_reserved_sanitization
    names=("${RESERVED_NAMES[@]}")
    for name in "${names[@]}"; do
      existing_token="$(read_existing_token "${name}")"
      if [ -n "${existing_token}" ]; then
        echo "Keeping existing token for ${name}"
        continue
      fi
      token="sk-local-${name}-$(python3 - <<'PY'
import secrets
print(secrets.token_hex(16))
PY
)"
      upsert_key_file "${name}" "${token}"
      echo "Generated token for ${name}"
    done
    write_keys_tmp_to_file
    echo "Current keys:"
    jq -r '.keys[] | "- \(.name): \(.token)"' "${KEYS_FILE}"
    ;;
  overwrite)
    load_keys_tmp
    apply_reserved_sanitization
    names=("${RESERVED_NAMES[@]}")
    for name in "${names[@]}"; do
      token="sk-local-${name}-$(python3 - <<'PY'
import secrets
print(secrets.token_hex(16))
PY
)"
      upsert_key_file "${name}" "${token}"
      echo "Generated token for ${name}"
    done
    write_keys_tmp_to_file
    echo "Current keys:"
    jq -r '.keys[] | "- \(.name): \(.token)"' "${KEYS_FILE}"
    ;;
  ensure-file)
    ensure_default_keys_file
    ;;
  sync-from-file)
    wait_for_litellm
    sync_file_to_remote
    ;;
  sync-init)
    run_sync_init
    ;;
esac
