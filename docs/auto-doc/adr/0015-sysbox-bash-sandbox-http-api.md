# 0015 - Sysbox Bash Sandbox HTTP API

- Status: Accepted
- Date: 2026-06-10
- OverheadSeconds: 0

## Context

Slice 1 provides a Sysbox-backed `sysbox_bash` Compose service with an inner Docker daemon.
Slice 2 adds a FastAPI Sandbox HTTP API (`container/sysbox-bash-image/app/`) so trusted lab
code can start stateful Bash sessions, execute scripts, and delete sessions without direct
Docker control from `dev`. Slice 3 consumes this API via the LangGraph bridge ([ADR 0014](0014-tool-node-sysbox-bash-langgraph-bridge.md)).

The API is a portable runtime boundary: limits, lifecycle, and artifact layout should remain
explicit when the execution backend changes.

## Decision

Keep Bash execution behind an **internal-only** FastAPI service owned by `sysbox_bash`:

- **Endpoints:** `GET /health`, `POST /sessions`, `POST /sessions/{session_id}/exec`,
  `DELETE /sessions/{session_id}`. No `GET /sessions` (lab visibility via
  `make sysbox-bash-sessions` only).
- **Lifecycle:** API-owned opaque `session_id` and monotonic `run_id` per session.
- **Execution:** script-as-file (`script.sh`) with captured `stdout.txt`, `stderr.txt`, and
  `metadata.json` under the service session tree.
- **Correlation:** optional trusted fields copied from request bodies into metadata
  (`graph_invoke_id`, `thread_id`, `subgraph_name`, `node_name`, `caller_label`,
  `request_id`, `tool_round`, `tool_call_id`). The LLM does not supply these.
- **Limits:** enforce `SBASH_MAX_SCRIPT_BYTES`, `SBASH_MAX_STDOUT_BYTES`,
  `SBASH_MAX_STDERR_BYTES`, and `SBASH_DEFAULT_TIMEOUT_SECONDS`. Per-run `timeout_seconds`
  may only **reduce** the default; over-default values return 4xx (no silent clamp).

**Runtime control surface** (operator-managed, portable across orchestrators):

- `SBASH_PORT`
- `SBASH_BIND_HOST` (optional; default auto-detects the Compose `backend_core` IPv4 from `hostname`; manual values must pass the same startup guards — reject `0.0.0.0`, `127.0.0.1`, and inner `docker0` IP)
- `SBASH_EXEC_IMAGE_NAME`, `SBASH_SESSIONS_ROOT`
- `SBASH_MAX_SCRIPT_BYTES`, `SBASH_MAX_STDOUT_BYTES`, `SBASH_MAX_STDERR_BYTES`
- `SBASH_DEFAULT_TIMEOUT_SECONDS`
- Compose service-level CPU/memory limits on `sysbox_bash` (`SBASH_CPUS`, `SBASH_MEM_LIMIT`, …)

**Lab network invariant (fixed):** session inner containers use the default inner `docker0`
bridge. The API binds only the trusted Compose interface (auto-detected `backend_core` IPv4 via
`hostname` → `sysbox_bash` → `eth0`, not `0.0.0.0`) and installs an idempotent `iptables`
`INPUT DROP` for inner-bridge sources to `${SBASH_PORT}`. Trusted `dev` traffic on
`backend_core` remains allowed; session containers keep outbound internet as an accepted lab
limitation.

**Explicit rejects for v1:** production-grade auth, host port publish by default, HTTPS/Caddy
routing on the internal path, session listing over HTTP, automatic session garbage collection.

Endpoint and operator detail: [`container/sysbox-bash-image/README.md`](../../../container/sysbox-bash-image/README.md).

This decision is currently in effect in production/dev workflow.

## Consequences

- Contract verification stays `make sysbox-bash-api-smoke` (not pytest L4); see [ADR 0011](0011-course-test-scope-layers.md).
  Negative smoke asserts session containers cannot reach the API on the `backend_core`
  bind IP (primary iptables invariant). A supplementary `docker0` gateway probe still
  fails if the API is reachable there, but a pass may reflect bind-only blocking.
- Accepted lab limitations (isolation grade, leaks, fairness, network) are documented in the
  sysbox service README — not repeated here.
- LangGraph session start/stop semantics remain in [ADR 0014](0014-tool-node-sysbox-bash-langgraph-bridge.md).
- API startup waits briefly for inner `docker0` CIDR before applying session firewall rules;
  `After=docker.service` plus `Restart=on-failure` cover longer inner-Docker timing glitches.
- **iptables failure is fail-closed:** `run-api.sh` applies the session firewall before uvicorn;
  insert is verified with `iptables -C`. Any firewall or bind error keeps the HTTP API down.
- **Lab assumption A1:** Sysbox system-container runtime is sufficient for `iptables INPUT`
  without extra Compose `cap_add`; portability to plain `runc` without review is not claimed.
