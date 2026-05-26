#!/bin/sh
set -eu
# Purpose: start JupyterLab inside the dev image runtime.
# Called by: keepalive.sh during container startup.
# Notes: prefers project venv kernel/runtime and falls back to base venv.

PROJECT_VENV="${PROJECT_VENV:-/workspace/src/.venv}"
BASE_VENV="${VIRTUAL_ENV:-/opt/venv}"

if [ -x "${PROJECT_VENV}/bin/jupyter" ]; then
  VENV_PATH="${PROJECT_VENV}"
else
  VENV_PATH="${BASE_VENV}"
fi

exec "${VENV_PATH}/bin/jupyter" lab \
  --ip=0.0.0.0 \
  --port="${JUPYTER_PORT:-8888}" \
  --no-browser \
  --ServerApp.token="${JUPYTER_TOKEN:?Set JUPYTER_TOKEN in container/compose/.env (or pass -e JUPYTER_TOKEN)}" \
  --ServerApp.password=''
