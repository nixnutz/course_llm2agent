#!/usr/bin/env bash
set -euo pipefail

if [ "$(uname -s 2>/dev/null || echo unknown)" != "Linux" ]; then
  echo "ERROR: sysbox_bash requires a Linux host with Sysbox." >&2
  exit 1
fi

runtimes="$(docker info --format '{{json .Runtimes}}' 2>/dev/null || true)"
if [ -z "${runtimes}" ] || ! printf '%s' "${runtimes}" | grep -q 'sysbox-runc'; then
  echo "ERROR: Docker runtime 'sysbox-runc' is not registered." >&2
  echo "Install Sysbox: https://github.com/nestybox/sysbox/blob/master/docs/user-guide/install.md" >&2
  exit 1
fi

if ! docker run --rm --runtime=sysbox-runc hello-world >/dev/null 2>&1; then
  echo "ERROR: sysbox-runc smoke test failed (docker run --runtime=sysbox-runc hello-world)." >&2
  echo "Verify Sysbox installation and that the daemon was restarted after install." >&2
  exit 1
fi
