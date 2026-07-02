# Course notebooks (`src/assorted`)

Index for the **course deliverable (sessions 1–8)**. Run notebooks with the **dev container** kernel.
Session **8** is still rough but belongs to the deliverable — the end-to-end parent graph demo.

The [course presentation](../../docs/toolbert_lab.pdf) explains the motivation: a deliberately tiny
agent task (mask email PII, extract TODOs, demask) inside **Toolbert Lab** — a supervised home for
LangGraph agents. Sessions walk from lab foundations toward **controlled capability**: state
boundaries and guards (3–5), safe tool wiring (6), Sysbox sandbox (7), then the full in-graph
pipeline (8).

Setup: [docs/getting-started.md](../../docs/getting-started.md)  
Pipeline map: [docs/course/pipeline-and-nodes.md](../../docs/course/pipeline-and-nodes.md)

If a notebook imports shared code under `src/` (e.g. `src.reducer`), run this once in the first code cell:

```python
import sys
sys.path.insert(0, "/workspace")
```

## Course sessions (1–8)

| Session | Focus | Notebooks |
|---------|--------|-----------|
| 1 | Chaos channel (Toxiproxy), home assignment | [`session1/chaos.ipynb`](session1/chaos.ipynb), [`session1/homeassignment.ipynb`](session1/homeassignment.ipynb) |
| 2 | RAG basics (vector search in the lab) | [`session2/rag_basics.ipynb`](session2/rag_basics.ipynb), [`session2/rag_pgvector.ipynb`](session2/rag_pgvector.ipynb) |
| 3 | LangGraph basics, message reducer | [`session3/langgraph.ipynb`](session3/langgraph.ipynb), [`session3/langgraph_messages.ipynb`](session3/langgraph_messages.ipynb) |
| 4 | Parent graph assembly (PII → TODO → demask) | [`session4/langgraph.ipynb`](session4/langgraph.ipynb) |
| 5 | Phoenix tracing, reducer observability | [`session5/graphtrace.ipynb`](session5/graphtrace.ipynb) |
| 6 | Tool subgraph with safe mock tool | [`session6/tool_node_basics.ipynb`](session6/tool_node_basics.ipynb) |
| 7 | Sandbox infrastructure (Sysbox HTTP API) | [`session7/tool_node_sysbox.ipynb`](session7/tool_node_sysbox.ipynb) |
| 8 | End-to-end parent graph (rough) — Sysbox + in-graph demask | [`session8/presentation.ipynb`](session8/presentation.ipynb) |

### Session 5 — tracing lab

`session5/graphtrace.ipynb` exercises the parent-graph sketch with Phoenix tracing (also used
as the temporary first-run exercise in getting started). After a **successful** invoke,
check the notebook console and Phoenix for **Observe-tier** log markers (`leak_suspected`,
`placeholder_violation`, `span_not_found`, `normalization_failed`) — the graph can complete
while soft-fail events are logged. Runtime contract:
[`docs/auto-doc/adr/0012-course-error-mode-contract.md`](../../docs/auto-doc/adr/0012-course-error-mode-contract.md).

### Session 6 — tool subgraph (mock tool)

`session6/tool_node_basics.ipynb` introduces the `tool_node_loop` subgraph: how tools plug into the
parent graph, policy limits, and tracing. The mock `greet()` tool is deliberately trivial — it keeps
blast radius small while the **infrastructure** (subgraph wiring, `ToolNode`, guards) is the
deliverable. Notebook-led; not wired into the parent-graph sketch yet.

### Session 7 — sandbox infrastructure (Sysbox)

`session7/tool_node_sysbox.ipynb` is the infrastructure capstone: a **lab sandbox** via the
`sysbox_bash` HTTP service and the `tool_node_sysbox_bash` LangGraph bridge. Powerful tools need
isolation — the notebook explains why Sysbox is used here as a deliberately simple, self-contained
prototype (HTTP decoupling, per-session sandboxes, accepted lab limits — not production security).
Service detail:
[`container/sysbox-bash-image/README.md`](../../container/sysbox-bash-image/README.md). Requires
healthy `sysbox_bash` (`make sysbox-bash-api-smoke`).

### Session 8 — end-to-end demo (rough)

`session8/presentation.ipynb` runs the **intended course end state**: full parent graph
(PII → TODO → Sysbox bash → demask on `final_result`). Still rough — notebook-led assembly,
not polished teaching prose — but part of the deliverable.

## Beyond the course (session 9+)

Follow-up experiments and ad-hoc notebooks may appear here without being part of the
course deliverable (sessions 1–8).

## Not indexed

| Item | Note |
|------|------|
| [`session3/langchain_chat_template.ipynb`](session3/langchain_chat_template.ipynb) | Scratchpad notebook — not part of the course index; archive/delete/keep pending decision |
