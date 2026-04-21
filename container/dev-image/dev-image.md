# Dev Image Contract (v1)

## Purpose

Provide a minimal, reproducible Python runtime for this course agent project.

## Fixed Requirements

1. Python latest GA target (to be pinned explicitly during implementation updates)
2. `venv` available
3. Baseline dependencies installed from `src/requirements.txt`
4. `ruff` available in baseline
5. `ipykernel` available in baseline for notebook integration
6. `jupyterlab` available in baseline and started with dev runtime
7. LiteLLM reachable via OpenAPI-compatible HTTP API

## Host vs Container Responsibilities

- Host: editor, Git, repository management
- Container: Python execution runtime only (default user `dev`)
- Source code: mounted into container

## Container Runtime Mode

- PID 1 is a trap-based keepalive script.
- Signals (`SIGINT`, `SIGTERM`) are handled for clean shutdown.
- Interactive development uses shell attach/exec into the running container.
- Jupyter server runs in the same service background during runtime.
- `/workspace/src/.venv` is bootstrapped automatically and provides the default notebook kernel.

## Privilege Model

- Default runtime user: `dev` (non-root, interactive shell available).
- `dev` has sudo with `NOPASSWD` for developer convenience.
- Root password is intentionally not configured.
- Optional direct root shell remains available from host-side container exec.

## Security Warning

`sudo` with `NOPASSWD` is intentionally a convenience trade-off for local development.
This is not a hardened posture for environments where an agent may execute arbitrary commands.
For stricter setups, remove `sudo` or gate privileged operations through explicit host-side controls.

## Python Packaging Contract

- No system-wide `pip install` into distro Python.
- Dedicated venv at `/opt/venv`.
- Baseline installs from `src/requirements.txt` during image build.
- Notebook integration uses baseline `ipykernel` and `jupyterlab`.
- Exploratory package installs happen in `/workspace/src/.venv` for zero-friction iteration.
- Promote durable dependencies to `src/requirements.txt` when experimentation stabilizes.

## LiteLLM API Contract

- `LITELLM_BASE_URL`: required
- `LITELLM_API_KEY`: optional
- `LITELLM_TIMEOUT_SECONDS`: required default

Do not hardcode endpoint URLs or tokens in source code.

## Verification Checklist

1. `python3 --version` works
2. `python --version` inside `/opt/venv` works
3. `whoami` returns `dev` in normal sessions
4. `sudo -n whoami` returns `root`
5. `ruff --version` works
6. Notebook mode can be started via `/usr/local/bin/start-notebook.sh`
7. Notebook server starts on demand only
8. Minimal Python HTTP call to LiteLLM endpoint succeeds
9. `git` command is not installed in container

## Change Policy

Any added tool/package must include:

- reason
- owner
- date
- expected learning/runtime value

## Dependency Change Log

Start empty in v1. Add entries only when requirements are approved.
