#!/bin/sh
# Purpose: shared dev runtime bootstrap for generated secret env variables.
# Called by: keepalive.sh, dev session wrapper, and dev cmd wrapper.
# Notes: orchestration-only; export logic stays in export-secrets-env.sh.

EXPORTER="${DEV_SECRETS_EXPORTER:-/workspace/compose-scripts/dev/export-secrets-env.sh}"
ENV_FILE="${DEV_SECRETS_ENV_FILE:-/tmp/dev-secrets.env.sh}"

if [ -x "${EXPORTER}" ]; then
  if ! "${EXPORTER}"; then
    echo "WARN: dev secrets export failed; runtime env variables may be missing" >&2
  fi
else
  echo "WARN: dev secrets exporter not found; skipping JSON->env injection" >&2
fi

if [ -f "${ENV_FILE}" ]; then
  # shellcheck disable=SC1090
  . "${ENV_FILE}"
fi
