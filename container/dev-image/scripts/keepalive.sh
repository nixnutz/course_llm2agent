#!/bin/sh
set -eu
# Purpose: container entrypoint that keeps dev runtime alive.
# Called by: Docker CMD in the dev image.
# Notes: runs startup bootstraps, launches notebook, and handles signals.

running=true
notebook_pid=""

handle_term() {
  running=false
  if [ -n "$notebook_pid" ]; then
    kill "$notebook_pid" 2>/dev/null || true
  fi
}

trap 'handle_term' INT TERM

if ! "/usr/local/bin/import-local-ca.sh"; then
  echo "WARN: local CA trust import failed; continuing without custom trust" >&2
fi

if ! "/usr/local/bin/bootstrap-project-venv.sh"; then
  echo "WARN: project venv bootstrap failed; falling back to base runtime" >&2
fi
"/usr/local/bin/start-notebook.sh" &
notebook_pid="$!"

while [ "$running" = "true" ]; do
  sleep 3600 &
  wait $!
done

wait "$notebook_pid" 2>/dev/null || true
