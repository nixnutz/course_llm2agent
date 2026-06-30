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

There is intentionally no `GET /sessions` endpoint. Use the host-side `make sysbox-bash-sessions` helper for lab visibility.

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

Optional:

- `SBASH_BIND_HOST` — force uvicorn bind address; default auto-detects the Compose `backend_core` IPv4 from `hostname`. Overrides are validated at startup (`0.0.0.0`, `127.0.0.1`, and inner `docker0` IP are rejected).

The API enforces `SBASH_MAX_SCRIPT_BYTES`, `SBASH_MAX_STDOUT_BYTES`, `SBASH_MAX_STDERR_BYTES`, and `SBASH_DEFAULT_TIMEOUT_SECONDS`. Optional per-run `timeout_seconds` may only reduce the timeout below the default; requests above the default return a 4xx response instead of being silently clamped.

Timeout and output-limit responses are structured lab conventions:

- timeout: `timed_out=true`, `exit_code=124`, `metadata.termination_reason="timeout"`
- output cap: `output_limit_exceeded=true`, `exit_code=137`, `metadata.termination_reason="output_limit_exceeded"`

## Verification

From repository root, after the stack is up and `sysbox_bash` is healthy:

```bash
make sysbox-bash-api-smoke
make sysbox-bash-sessions
```

The smoke test covers the API without LangGraph: health, session start, same-session state, non-zero exit, timeout, over-default timeout rejection, script-size rejection, stdout/stderr output limits, dummy and omitted correlation metadata, absence of `GET /sessions`, session-side negative checks (primary: `backend_core` bind IP must be unreachable from sessions; supplementary: inner `docker0` gateway), optional outbound internet probe, and cleanup.

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
- **No extra `cap_add` for iptables (lab assumption A1):** the Sysbox **system container**
  is expected to grant enough privilege for `iptables INPUT` inside the service namespace.
  Compose does not add capabilities; if firewall setup fails, `sysbox-bash-api.service` exits
  **before** uvicorn starts (`run-api.sh` order: bind resolve → iptables → API). The HTTP
  service stays down until firewall + bind succeed (`Restart=on-failure` on the unit).

## Known limitations (accepted for the lab)

This Sandbox API is a **learning boundary**, not a production execution platform.
See also [ADR 0015](../../docs/auto-doc/adr/0015-sysbox-bash-sandbox-http-api.md).

| Area | Behavior today | If it breaks |
|------|----------------|--------------|
| **Isolation** | Sysbox DinD system container; lab-grade only | Treat Sysbox escape as serious; do not promise enterprise sandbox hardening |
| **HTTP exposure** | Internal Compose network; binds `backend_core` IP only; `iptables` blocks inner `docker0` sources to `SBASH_PORT`; no v1 auth; no host port by default | Do not expose the API outside the lab network without a separate security review |
| **Script/output limits** | 32 KiB script; 256 KiB stdout/stderr per run; timeout may only reduce `SBASH_DEFAULT_TIMEOUT_SECONDS` | Over-limit runs stop with structured `timed_out` / `output_limit_exceeded` responses |
| **Session leaks** | Crashes, partial HTTP failures, or hard kernel kill may leave inner containers | No automatic GC; recovery = `make sysbox-bash-service-restart` and `make sysbox-bash-sessions` |
| **Fairness** | Single-user lab; service-level CPU/memory cap on `sysbox_bash` | Multiple sessions share the budget; per-session fairness is out of scope |
| **Observability** | Basic run metadata only | Scripts/outputs may also appear in LangGraph messages, Phoenix traces, or notebook output |
| **Network** | Outbound internet allowed inside the session; Sandbox API blocked from session containers (bind + `iptables`) | Document clearly: not production-safe for untrusted code |
| **Bash name vs Python runtime** | **TODO / gap:** `sysbox-bash` naming and the `bash` tool suggest Bash-only sessions; the exec image is `python:3.11-bookworm` with Bash as shell — Python is available and used by `api-smoke` | Do not claim Bash-only isolation; see [`sysbox-bash-exec-image/README.md`](../sysbox-bash-exec-image/README.md#todo--gap--name-says-bash-runtime-is-python-based) |

## Troubleshooting

```bash
docker compose exec sysbox_bash systemctl status docker.service
docker compose exec sysbox_bash systemctl status sysbox-bash-load-exec-image.service
docker compose exec sysbox_bash systemctl status sysbox-bash-api.service
docker compose exec sysbox_bash journalctl -u sysbox-bash-load-exec-image.service --no-pager
docker compose exec sysbox_bash journalctl -u sysbox-bash-api.service --no-pager
```

If `sysbox-bash-api.service` fails at startup with `could not resolve docker0 CIDR`, inner
Docker may not have created `docker0` yet. The firewall script retries for up to 30 seconds;
`Restart=on-failure` on the unit covers longer glitches. Check `docker.service` first.
