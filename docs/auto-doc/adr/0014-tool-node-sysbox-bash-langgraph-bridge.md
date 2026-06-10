# 0014 - tool_node_sysbox_bash LangGraph Bridge and Sandbox Session Lifecycle

- Status: Accepted
- Date: 2026-06-10
- OverheadSeconds: 0

## Context

Slice 2 exposes Bash execution via an internal Sandbox HTTP API (`container/sysbox-bash-image/`). The course pipeline already has a mock-tool subgraph (`tool_node_loop`) that turns structured TODO JSON into markdown. Session 7 needs real Bash in an isolated sandbox without changing `GlobalState` or the HTTP API boundary.

## Decision

Add a separate LangGraph package `src/llm_nodes/tool_node_sysbox_bash/` (does not replace `tool_node_loop`).

**Bridge-owned sandbox lifecycle:** `make_tool_node_sysbox_bash_subgraph_runner` requires `SBASH_BASE_URL`, calls `start_session`, passes `sandbox_session_id` into subgraph initial state, and calls `end_session` in a `finally` block. The compiled subgraph has no `start_sandbox` / `cleanup_sandbox` nodes.

**State and I/O:** Subgraph input is `todo_list_json`; internal deliverable is `result_text`. The bridge maps `result_text` → `GlobalState.todo_text`. No `GlobalState` schema change in Slice 3.

**Tools:** Custom `run_tools` reads `state.sandbox_session_id` and calls the HTTP client. `@tool bash` exists only for `bind_tools` schema; execution is not via prebuilt `ToolNode`. Tool failures surface as `ToolMessage` text (observe tier per [ADR 0012](0012-course-error-mode-contract.md)); `policy_exhausted` raises `PolicyViolationError`.

**Trusted finalize:** Who-placeholder audit only (same pattern as `tool_node_loop`); lab word-count/reverse task is prompt guidance, not a trusted transform gate.

**Policy limits:** `max_tool_rounds` / `max_tool_errors` from shared `src/llm_nodes/tool_node_policy.py`, scaled from TODO item count.

**Tests:** [ADR 0011](0011-course-test-scope-layers.md) exemplars only — L1 policy/router/finalize and one L3 scripted subgraph with mock `SandboxClient`. API contract smoke stays `make sysbox-bash-api-smoke`; optional E2E via `src/assorted/session7/tool_node_sysbox.ipynb`.

This decision is currently in effect in production/dev workflow.

## Consequences

- Operators must keep `sysbox_bash` healthy and `SBASH_BASE_URL` set in the dev runtime before the bridge runs.
- Session leaks on hard kill remain a lab concern; normal subgraph exceptions still hit bridge `finally`.
- A dedicated Sandbox HTTP ADR may still be added for Slice 2; this ADR covers only the LangGraph client/bridge contract.
