#!/usr/bin/env bash
set -euo pipefail
# Purpose: validate and normalize local virtual key JSON for reserved names.
# Called by: one-shot container service "litellm_keys_file_gate".
# Notes: ensures file shape and reserved entries before LiteLLM key sync.

KEYS_FILE="${KEYS_FILE:-.state/keys/keys.local.json}"

python3 - <<'PY'
import json, os, secrets, pathlib

keys_path = pathlib.Path(os.environ.get("KEYS_FILE", ".state/keys/keys.local.json"))

allowed = ["dev", "stage", "prod", "user1", "user2"]

def gen_token(name: str) -> str:
    return f"sk-local-{name}-{secrets.token_hex(16)}"

if keys_path.exists():
    raw = keys_path.read_text(encoding="utf-8").strip() or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SystemExit(f"Invalid JSON in {keys_path}: {e}")

    if not isinstance(data, dict) or "keys" not in data or not isinstance(data["keys"], list):
        raise SystemExit(f"Invalid structure in {keys_path}: expected object with keys[] list")

    by_name = {}
    removed = []
    for item in data["keys"]:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        token = item.get("token")
        if not name or not token:
            continue
        name = str(name)
        token = str(token)
        if name not in allowed:
            removed.append(name)
            continue
        by_name[name] = {"name": name, "token": token}

    changed = False
    if removed:
        changed = True

    for name in allowed:
        if name not in by_name:
            by_name[name] = {"name": name, "token": gen_token(name)}
            changed = True

    out = {"keys": [by_name[n] for n in allowed]}
    if changed:
        keys_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        try:
            os.chmod(keys_path, 0o600)
        except OSError:
            pass
else:
    out = {"keys": [{"name": n, "token": gen_token(n)} for n in allowed]}
    keys_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(keys_path, 0o600)
    except OSError:
        pass

print(f"OK: {keys_path} is present and contains the five reserved keys.")
PY
