# Error handling (course)

How the **current work-in-progress** course pipeline reacts when something goes wrong.
This is a **runtime behavior sketch** for labs and tests — not production compliance and
not a coding style guide. Policy and graph shape may change as sessions land.

## Teaching default: Mode C

**Observe inside the pipeline:** log and trace problems; the graph may still complete when
LLM output quality drifts. You audit behavior via application logs and Phoenix traces.

Stricter **egress** (for example fatal abort before `demask`) is documented but not
implemented in the current parent-graph sketch (WIP).

Normative contract: [ADR 0012 — course error-mode contract](../auto-doc/adr/0012-course-error-mode-contract.md).

## Three tiers

| Tier | Reaction today | Examples |
|------|----------------|----------|
| **Guard** | `raise` on bad input before an untrusted step | Invalid state before LLM calls; `PipelinePreconditionError`, `PipelineValidationError`, `PolicyViolationError` (`src/errors.py`) |
| **Observe** | Warning logs (+ trace); pipeline continues | `leak_suspected`, `placeholder_violation`, `span_not_found`, `normalization_failed` |
| **Library** | Dependency errors propagate (not swallowed) | Network/API failures from LiteLLM, Ollama, httpx |

Mode C means Guard and Observe use **log + trace** inside the graph; Library-tier failures
still abort the run.

### Guard exception types (`src/errors.py`)

| Type | Base | Typical cause |
|------|------|----------------|
| `PipelinePreconditionError` | `ValueError` | Missing or empty required state before a step |
| `PipelineValidationError` | `ValueError` | Deterministic check on a produced deliverable failed |
| `PolicyViolationError` | `Exception` | Loop/policy limit hit while work is still pending |

`PipelinePreconditionError` and `PipelineValidationError` remain catchable via
`except ValueError`. `PolicyViolationError` is intentionally separate — a broad
`except ValueError` does not catch policy exhaustion; handle it explicitly in tests
and graph callers.

## Where to see it

| Surface | Pointer |
|---------|---------|
| Tracing lab | `src/assorted/session5/graphtrace.ipynb` — run cell 0 first; check Phoenix after invoke |
| Session 5 README | `src/assorted/README.md` |
| PII / placeholder policy | `src/llm_nodes/pii_email/README.md`, `src/llm_nodes/placeholder_audit/README.md` |
| L6 chaos exemplars | `src/tests_and_evals/tests/graphs/test_parent_base_graph_chaos.py` — Library-tier propagation |
| Test layers | `src/tests_and_evals/README.md` — L6 chaos after error contract is documented |

## Related docs

- [Pipeline and nodes](pipeline-and-nodes.md) — where demask sits in the trusted boundary
- [Editor and agent workflow](../editor-and-agent-workflow.md) — how contributors work in this repo (separate from runtime tiers)
