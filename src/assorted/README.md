# Course notebooks (`src/assorted`)

**Work in progress** — sessions land over the semester; notebooks and `src/graphs/` may
not always match.

Run with the **dev container** kernel. Setup: [docs/getting-started.md](../../docs/getting-started.md).
Pipeline map (current sketch): [docs/course/pipeline-and-nodes.md](../../docs/course/pipeline-and-nodes.md).

If a notebook imports shared code under `src/` (e.g. `src.reducer`), run this once in the first code cell:

```python
import sys
sys.path.insert(0, "/workspace")
```

## Session 5 tracing lab (current sketch)

`session5/graphtrace.ipynb` exercises the **current** parent-graph sketch with Phoenix
tracing (also used as the temporary first-run exercise in getting started). After a
**successful** invoke, check the notebook console and Phoenix for **Observe-tier** log
markers (`leak_suspected`, `placeholder_violation`, `span_not_found`,
`normalization_failed`) — the graph can complete while soft-fail events are logged.
Runtime contract: [`docs/auto-doc/adr/0012-course-error-mode-contract.md`](../../docs/auto-doc/adr/0012-course-error-mode-contract.md).

## Session 6 — tool loop (mock `greet`)

`session6/tool_node_basics.ipynb` — ReAct loop with `tool_node_loop` and `greet(who)`; notebook-led, not wired into the parent-graph sketch yet.

## Session 7 — tool loop (Sysbox `bash`)

`session7/tool_node_sysbox.ipynb` — E2E smoke for `tool_node_sysbox_bash` via `SBASH_BASE_URL`. Requires healthy `sysbox_bash` (`make sysbox-bash-api-smoke`). Teaching prose is author-owned (Slice 4 deferred).
