# Sysbox Bash service image

Sysbox **system container** for the `sysbox_bash` Compose service: systemd (PID 1) plus inner Docker.

This is **not** the per-session exec image (`container/sysbox-bash-exec-image/`).

## Build

From repository root:

```bash
make sysbox-bash-image-build
```

Requires Docker on the host. The Compose service also requires `sysbox-runc` (see `container/compose/scripts/sysbox_bash/preflight.sh`).

## API contract (Slice 2)

The FastAPI service exposes the Sandbox HTTP API on the internal Compose network:

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Readiness probe; returns 503 until inner Docker and the exec image are ready |
| `POST /sessions` | Start a stateful inner Bash session container |
| `POST /sessions/{session_id}/exec` | Execute one Bash script in an existing session |
| `DELETE /sessions/{session_id}` | Remove a session container and its runtime state |

`POST /sessions` accepts optional trusted session correlation fields:
`graph_invoke_id`, `thread_id`, `subgraph_name`, `node_name`, and `caller_label`.

`POST /sessions/{session_id}/exec` accepts optional trusted run correlation fields:
`request_id`, `tool_round`, and `tool_call_id`.

Slice 2 stores these values in run metadata. Slice 3 is responsible for filling them from LangGraph `RunnableConfig`, graph state, and tool-call context.

Each run uses script-as-file execution and writes artifacts under the service-local session tree:

- `script.sh`
- `stdout.txt`
- `stderr.txt`
- `metadata.json`

The API reads required runtime configuration from environment variables and fails fast when any required value is missing or invalid. Compose should provide these explicitly from `.env` / `.env.example`; the app does not keep hidden fallback defaults.

Required API runtime variables:

- `SBASH_EXEC_IMAGE_NAME`
- `SBASH_SESSIONS_ROOT`
- `SBASH_MAX_SCRIPT_BYTES`
- `SBASH_MAX_STDOUT_BYTES`
- `SBASH_MAX_STDERR_BYTES`
- `SBASH_DEFAULT_TIMEOUT_SECONDS`

The API enforces `SBASH_MAX_SCRIPT_BYTES`, `SBASH_MAX_STDOUT_BYTES`, `SBASH_MAX_STDERR_BYTES`, and `SBASH_DEFAULT_TIMEOUT_SECONDS`. Optional per-run `timeout_seconds` may only reduce the timeout below the default.

## Verification

From repository root, after the stack is up and `sysbox_bash` is healthy:

```bash
make sysbox-bash-api-smoke
make sysbox-bash-sessions
```

The smoke test covers the API without LangGraph: health, session start, same-session state, non-zero exit, timeout, script-size rejection, stdout/stderr output limits, correlation metadata, and cleanup.

`make sysbox-bash-sessions` is not part of the Sandbox HTTP API. It is a host-side lab helper that uses `docker compose exec sysbox_bash docker ps` to inspect managed inner containers.

## Spike verification (Slice 1)

| Spike | Check |
|-------|--------|
| S0 | `docker compose exec sysbox_bash systemctl is-active docker.service` → `active` |
| S1 | `docker compose exec sysbox_bash docker run --rm hello-world` |
| S2 | `docker compose exec sysbox_bash docker images` shows exec image tag |
| S3 | `GET http://sysbox_bash:8080/health` → 200 |

## Environment variable naming

Compose service name: `sysbox_bash`. Container env uses **`SBASH_*`** (not `SYSBOX_*`) because the Sysbox runtime reserves `SYSBOX_` names for its own configuration.

## Compose constraints

- `runtime: sysbox-runc` on the host
- **Do not** set `init: true` on this service — systemd must remain PID 1
- No `entrypoint` / `command` overrides

## Troubleshooting

```bash
docker compose exec sysbox_bash systemctl status docker.service
docker compose exec sysbox_bash systemctl status sysbox-bash-load-exec-image.service
docker compose exec sysbox_bash systemctl status sysbox-bash-api.service
docker compose exec sysbox_bash journalctl -u sysbox-bash-load-exec-image.service --no-pager
docker compose exec sysbox_bash journalctl -u sysbox-bash-api.service --no-pager
```
