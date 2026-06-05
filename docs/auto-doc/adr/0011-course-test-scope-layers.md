# 0011 - Course Test Scope Layers (Reminder, Not Exhaustive)

- Status: Accepted
- Date: 2026-06-04
- OverheadSeconds: 0

## Context

The course pipeline (`src/llm_nodes/`, `src/graphs/`, `src/other_nodes/`) mixes deterministic Python, mocked LLM wiring, compiled LangGraph parents, smoke integration, and golden-set evals. Without a shared scope model, reviews re-debate how much to test on every change. Tests are **reminders** that critical contracts and wiring exist — not a coverage quota.

## Decision

Use six layers. Each layer needs at least one **exemplar** test when the artifact is stable enough to test; deeper layers do not replace shallower ones for logic (L3 does not replace L1).

| Layer | Purpose | Marker(s) | Min exemplar |
|-------|---------|-----------|--------------|
| **L1** Unit (deterministic) | Pure Python pipelines, no LLM | `unit` | Per contract module (`mask.py`, `placeholder_audit`, …) |
| **L2** Node wiring | `get_*_node` guards + return shape | `unit` | Per node **or** covered by L3 for that pipeline (case-by-case) |
| **L3** Graph mock E2E | Full in-process graph; LLMs mocked | `unit` | One test per compiled top-level graph |
| **L4** Smoke | Real LLM, happy path | `integration`, `smoke` | Optional per LLM node on teaching path; skip without env |
| **L5** Eval | Golden-set quality | `eval` | Per eval-worthy dimension ([ADR 0010](0010-eval-must-should-pytest-hooks.md)) |
| **L6** Chaos/resilience | Real LLM via chaos channel ([ADR 0006](0006-toxiproxy-chaos-channel-architecture.md)) | `integration`, `chaos` | One exemplar per chaos-relevant path; **after** error-mode contract is defined |

**L2 detail:** LLM nodes use a mocked OpenAI client. Trusted non-LLM nodes (e.g. `demask_node`) use no LLM mock — only state wiring; logic stays in L1.

**L2 vs L3:** At least L2 **or** L3 per pipeline node. Prefer L2 when the node is reused in isolation or guards are not visible in L3; L3 suffices when an L2 test would only duplicate the graph path.

**Review vs commit:** Missing exemplar on the responsible layer = documentable review finding. Missing branch coverage = not a finding. **Commits without tests are allowed** when code is still moving; review notes the open layer and follow-up is enough. This ADR may land before all exemplar tests exist.

**Non-goals:** coverage quotas; re-testing L1 logic inside L3; smoke instead of L3 mock E2E; building L6 before error-mode behavior is decided.

Future MAS orchestrator graphs follow the same L3 rule as `build_parent_base_graph`.

Module docstrings: *"Not exhaustive: course/WIP"* plus pointer to the deeper layer.

This decision is currently in effect in production/dev workflow.

## Consequences

- Agents and review cite ADR 0011 instead of renegotiating scope.
- Fast CI default: `pytest tests_and_evals/tests -m "not eval"` (L6 chaos excluded unless selected).
- `@pytest.mark.chaos` registered in `src/pyproject.toml`.
- Normative pointer in `src/tests_and_evals/README.md`.
