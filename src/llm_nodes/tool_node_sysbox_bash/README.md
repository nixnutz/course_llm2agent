# tool_node_sysbox_bash (course sketch)

Separate LangGraph subgraph for Session 7: real `bash(script)` via HTTP to the Sysbox
Sandbox API. Does not replace `tool_node_loop`.

## What is in scope here

- ReAct loop: `llm_with_bash` → `run_tools` → `bump_tool_policy`; optional transport-retry
  branch `llm_fence_retry` → `run_fence_retry` (visible in `graph.py`)
- Parent **bridge** owns sandbox lifecycle: `start_session` → subgraph → `finally end_session`
- Subgraph deliverable `result_text` mapped to `GlobalState.todo_text` and `GlobalState.final_result` (demask slot)
- L1+L3 mock exemplar tests under `src/tests_and_evals/tests/llm_nodes/tool_node_sysbox_bash/`

## Bridge-specific limitations

| Area | Behavior today | If it breaks |
|------|----------------|--------------|
| **`SBASH_BASE_URL`** | Required before bridge runs; healthy `sysbox_bash` expected | Fail-fast at bridge entry |
| **Cleanup** | `end_session` in bridge `finally` on normal subgraph completion/exception | Hard kernel kill between `start_session` and `try` may still leak — same class as service-level leaks |
| **Trusted finalize** | Who-placeholder check only; word-count/reverse task is prompt guidance | See `tool_node_loop` pattern for placeholder audit |
| **Non-zero bash exit** | `format_exec_result` prefixes `Error:` → `tool_errors` increments via `_tool_message_failed` | `exit_code=0` with stderr warnings still passes (lab) |
| **Transport retry** | One free fence retry on `exit_code=2` + stderr parse/quote heuristics; `Transport retry:` offer does not increment `tool_errors` | After retry used, all failures count normally; happy path still `bind_tools` + `tool_calls` |
| **Bash tool name** | **TODO / gap:** tool/schema say `bash`; session exec image is Python-based (`python:3.11-bookworm`) — not Bash-only | See exec image README; do not overstate “Bash sandbox” in teaching prose |

Sandbox service limits (isolation, output caps, leaks, network): see
[`container/sysbox-bash-image/README.md`](../../../container/sysbox-bash-image/README.md#known-limitations-accepted-for-the-lab).

## Tests

- **L1+L3 unit exemplars:** `pytest tests_and_evals/tests/llm_nodes/tool_node_sysbox_bash/ -m unit`
- **API contract:** `make sysbox-bash-api-smoke` (not duplicated as pytest integration — fragile Sysbox host dependency; see [ADR 0011](../../../docs/auto-doc/adr/0011-course-test-scope-layers.md))
- **Bridge `finally`:** deferred integration exemplar per Slice 3 plan
- **Notebook E2E:** optional manual via `src/assorted/session7/tool_node_sysbox.ipynb` (author-owned prose in Slice 4)

## References

- ADR: [0014 LangGraph bridge](../../../docs/auto-doc/adr/0014-tool-node-sysbox-bash-langgraph-bridge.md)
- ADR: [0015 Sandbox HTTP API](../../../docs/auto-doc/adr/0015-sysbox-bash-sandbox-http-api.md)
- Error-mode contract: [ADR 0012](../../../docs/auto-doc/adr/0012-course-error-mode-contract.md)
