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
- `SBASH_EXEC_IMAGE_NAME`, `SBASH_SESSIONS_ROOT`
- `SBASH_MAX_SCRIPT_BYTES`, `SBASH_MAX_STDOUT_BYTES`, `SBASH_MAX_STDERR_BYTES`
- `SBASH_DEFAULT_TIMEOUT_SECONDS`
- Compose service-level CPU/memory limits on `sysbox_bash` (`SBASH_CPUS`, `SBASH_MEM_LIMIT`, …)

**Explicit rejects for v1:** production-grade auth, host port publish by default, HTTPS/Caddy
routing on the internal path, session listing over HTTP, automatic session garbage collection.

Endpoint and operator detail: [`container/sysbox-bash-image/README.md`](../../../container/sysbox-bash-image/README.md).

This decision is currently in effect in production/dev workflow.

## Consequences

- Contract verification stays `make sysbox-bash-api-smoke` (not pytest L4); see [ADR 0011](0011-course-test-scope-layers.md).
- Accepted lab limitations (isolation grade, leaks, fairness, network) are documented in the
  sysbox service README — not repeated here.
- LangGraph session start/stop semantics remain in [ADR 0014](0014-tool-node-sysbox-bash-langgraph-bridge.md).
