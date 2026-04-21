#!/bin/sh
set -eu

PROJECT_DIR="${PROJECT_DIR:-/workspace/src}"
PROJECT_VENV="${PROJECT_VENV:-${PROJECT_DIR}/.venv}"
KERNEL_NAME="${KERNEL_NAME:-course-llm-dev}"
KERNEL_DISPLAY_NAME="${KERNEL_DISPLAY_NAME:-Python (course-llm-dev)}"
BASE_PYTHON="${BASE_PYTHON:-/opt/venv/bin/python}"

mkdir -p "${PROJECT_DIR}"

if [ -d "${PROJECT_VENV}" ]; then
  if [ ! -w "${PROJECT_VENV}" ]; then
    sudo chown -R dev:dev "${PROJECT_VENV}" || true
  fi
fi

if [ ! -x "${PROJECT_VENV}/bin/python" ] || [ ! -x "${PROJECT_VENV}/bin/pip" ]; then
  rm -rf "${PROJECT_VENV}"
  cp -a /opt/venv "${PROJECT_VENV}"
  chown -R dev:dev "${PROJECT_VENV}"
fi

if ! "${PROJECT_VENV}/bin/python" -c "import ipykernel" >/dev/null 2>&1; then
  "${PROJECT_VENV}/bin/pip" install --no-cache-dir ipykernel
fi

if ! "${PROJECT_VENV}/bin/python" -c "import jupyterlab" >/dev/null 2>&1; then
  "${PROJECT_VENV}/bin/pip" install --no-cache-dir jupyterlab
fi

"${PROJECT_VENV}/bin/python" -m ipykernel install \
  --user \
  --name "${KERNEL_NAME}" \
  --display-name "${KERNEL_DISPLAY_NAME}"
