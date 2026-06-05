# Course notebooks (`src/assorted`)

Run with the **dev container** kernel (see `container/compose/README.md`).

If a notebook imports shared code under `src/` (e.g. `src.reducer`), run this once in the first code cell:

```python
import sys
sys.path.insert(0, "/workspace")
```

## Session 5 tracing lab

`session5/graphtrace.ipynb` runs the parent graph with Phoenix tracing. After a
**successful** invoke, check the notebook console and Phoenix for **Observe-tier** log
markers (`leak_suspected`, `placeholder_violation`, `span_not_found`,
`normalization_failed`) — the graph can complete while soft-fail events are logged.
Runtime contract: [`docs/auto-doc/adr/0012-course-error-mode-contract.md`](../../docs/auto-doc/adr/0012-course-error-mode-contract.md).
