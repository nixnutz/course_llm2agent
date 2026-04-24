#!/usr/bin/env bash
set -euo pipefail
# Purpose: bootstrap/sync reserved LiteLLM virtual keys from local key file.
# Called by: one-shot container service "litellm_init_keys".
# Notes: delegates to virtual-keys.sh in sync-init mode.

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "${SCRIPT_DIR}"

./virtual-keys.sh sync-init
