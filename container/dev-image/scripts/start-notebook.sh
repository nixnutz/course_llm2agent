#!/bin/sh
set -eu

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
  --ServerApp.token="${JUPYTER_TOKEN:-change_me}" \
  --ServerApp.password=''
