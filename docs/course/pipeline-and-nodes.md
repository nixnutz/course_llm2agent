# Pipeline and nodes

Map of the **current work-in-progress** parent-graph sketch in `src/graphs/`. The chain,
modules, and session notebooks will change during the course — this is a teaching
scratchpad, not a shipped agent product.

Session notebooks remain the primary walkthrough; this page is an orientation map.

## Parent graph chain (current sketch)

Factory (WIP): `build_parent_base_graph()` in `src/graphs/parent_base_graph.py`. The graph
assembly in code and in session notebooks may diverge until the course catches up.

```mermaid
flowchart LR
  START --> pii_extract_node
  pii_extract_node --> todo_extract_node
  todo_extract_node --> todo_markdown_node
  todo_markdown_node --> demask_node
  demask_node --> END
```

| Step | Kind | Role |
|------|------|------|
| `pii_extract_node` | LLM detect + Python mask | Find emails, replace with placeholders (`E{n}_{salt}`) |
| `todo_extract_node` | Subgraph (bridge) | Structured TODO list from masked text |
| `todo_markdown_node` | Subgraph (bridge) | Markdown summary from TODO list |
| `demask_node` | Deterministic | Restore placeholders to original emails in outputs |

Shared state: `GlobalState` in `src/llm_nodes/global_state.py` (`messages`, `pii_email`,
`todo_list`, `todo_markdown`).

## Subgraph and bridge pattern

TODO work runs in **isolated subgraphs** (`todo_extract`, `todo_markdown`) compiled on
smaller state types. **Bridges** in `src/llm_nodes/todo_extract/graph.py` and
`todo_markdown/graph.py`:

- Pass **masked text** and a **placeholder allowlist** (token strings only — no raw emails)
  into the subgraph.
- Merge subgraph results back onto `GlobalState`.
- Forward LangGraph `config` (thread id, tracing) into nested `ainvoke`.

After each subgraph LLM step, **placeholder audit** checks output tokens against the
allowlist (Observe tier today). See `src/llm_nodes/placeholder_audit/README.md`.

## Cross-cutting: `messages` and reducer

`GlobalState.messages` uses `session_message_reducer` — policy hooks outside individual
nodes (read/transform on message traffic). Wrap runs in `reducer_session` so the active
reducer applies per `thread_id`.

Introduction: `src/reducer/__init__.py` (module docstring). Notebook demo:
`src/assorted/session3/langgraph_messages.ipynb`.

## LLM client channels

Nodes use `src/llm_handle/local.py` (`get_async_openai_client`, `openai_client_context`):

- **Clean channel** — `MODEL_BASE_URL_CLEAN` (baseline path)
- **Chaos channel** — `MODEL_BASE_URL_CHAOS` (edge/provider faults via Toxiproxy)

`build_parent_base_graph(..., chaos=True)` selects the chaos base URL for course L6 tests.

## Module map

| Module | README / entry |
|--------|----------------|
| PII email | `src/llm_nodes/pii_email/README.md` |
| Placeholder audit | `src/llm_nodes/placeholder_audit/README.md` |
| TODO extract / markdown | `src/llm_nodes/todo_extract/graph.py`, `todo_markdown/graph.py` |
| Tool loop (mock `greet`) | `src/llm_nodes/tool_node_loop/` — Session 6; not in parent sketch yet |
| Tool loop (Sysbox `bash`) | `src/llm_nodes/tool_node_sysbox_bash/README.md` — Session 7; HTTP → `sysbox_bash` |
| Demask | `src/other_nodes/demask/` |
| Parent graph (WIP) | `src/graphs/parent_base_graph.py` |

## Notebooks (by session)

| Session | Focus |
|---------|--------|
| 3 | LangGraph basics, reducer messages |
| 4 | Parent graph assembly (notebook-led; `src/graphs/` mirrors when synced) |
| 5 | Phoenix tracing on current parent-graph sketch — `session5/graphtrace.ipynb` (temporary first-run exercise in getting started) |
| 6 | ReAct tool loop with mock `greet` — `session6/tool_node_basics.ipynb` (`tool_node_loop`; notebook-led, not in parent sketch) |
| 7 | ReAct tool loop with Sysbox `bash` — `session7/tool_node_sysbox.ipynb` (`tool_node_sysbox_bash`; E2E smoke; teaching prose author-owned) |

Index: `src/assorted/README.md`.

## Tests

| Layer | What |
|-------|------|
| L1–L2 | Unit / node mocks — `src/tests_and_evals/tests/llm_nodes/` |
| L3 | Parent graph mock E2E — `test_parent_base_graph_mock.py`; Sysbox subgraph mock — `tool_node_sysbox_bash/` |
| L6 | Chaos via Toxiproxy — `test_parent_base_graph_chaos.py` |

Sysbox Sandbox API contract (outside pytest layers): `make sysbox-bash-api-smoke`.

Marker and env requirements: `src/tests_and_evals/README.md`.

## Related

- [Error handling](error-handling.md) — Guard / Observe / Library on this pipeline
- [Getting started](../getting-started.md) — start the agent lab and first exercise in `dev`
- [ADR 0009 — PII pipeline](../auto-doc/adr/0009-pii-email-masking-pipeline.md)
- [ADR 0014 — Sysbox LangGraph bridge](../auto-doc/adr/0014-tool-node-sysbox-bash-langgraph-bridge.md)
- [ADR 0015 — Sandbox HTTP API](../auto-doc/adr/0015-sysbox-bash-sandbox-http-api.md)
