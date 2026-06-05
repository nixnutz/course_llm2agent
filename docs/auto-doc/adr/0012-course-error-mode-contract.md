# 0012 - Course Error-Mode Contract (Observe Inside, Deferred Strict Egress)

- Status: Accepted
- Date: 2026-06-04
- OverheadSeconds: 0

## Context

The course pipeline mixes LLM nodes, deterministic guards, and soft-fail log markers (`leak_suspected`, `placeholder_violation`). Without a shared reaction model, reviews re-debate when to abort versus log-and-continue. [ADR 0011](0011-course-test-scope-layers.md) L6 chaos tests needed a documented runtime contract before exemplars are added.

This is a **course teaching sketch** — always log and enable audit via project logs and Phoenix traces; not production compliance or EU AI Act implementation.

## Decision

**Default: Mode C** — observe inside the pipeline (log + trace); tolerate LLM variance during labs and MAS work. **Stricter later:** fatal reactions at trusted egress (Mode B) are documented but not implemented in this change.

### Three runtime reaction tiers (today)

| Tier | When | Reaction today |
|------|------|----------------|
| **Guard** | Invalid input/state before an untrusted step | `raise` (after log if any) |
| **Observe** | LLM quality / integrity drift with safe degradation | `logger.warning` / `logger.error`, **continue** |
| **Library** | Client/network/schema failures from dependencies | **propagate** (no swallow) |

Examples: `ValueError` and `ParseLLMJson` (Guard); `span_not_found`, `normalization_failed`, `leak_suspected` in `mask.py`, `placeholder_violation` in `placeholder_audit` (Observe); OpenAI/httpx errors on LLM calls, Pydantic `extra=forbid` on state (Library).

### Trusted egress boundary (future — not a fourth tier today)

A **trusted egress boundary** (e.g. before or at `demask_node`) is a *planned strictening* of selected Observe markers — not a separate runtime tier until implemented. Candidate: make accumulated `placeholder_violation` **fatal** before restore. `leak_suspected` remains audit-only unless explicitly revisited.

### Eval vs runtime

Golden-set eval gates ([ADR 0010](0010-eval-must-should-pytest-hooks.md), L5 in [ADR 0011](0011-course-test-scope-layers.md)) judge quality **after** a run; they do not replace Guard, Observe, or Library behavior during execution.

### Teaching hooks (discussion only)

- **Traceability** → logs + Phoenix (record-keeping as a course discussion hook).
- **Data minimization** → placeholders in subgraphs ([ADR 0009](0009-pii-email-masking-pipeline.md)).
- **Risk-appropriate degradation** → mask even when restore is uncertain (`email=None`).
- **Human oversight** → notebook/session, not autonomous delivery.

### Future L6 chaos expectations (tests not in scope of ADR 0012)

When chaos exemplars are added ([ADR 0006](0006-toxiproxy-chaos-channel-architecture.md), L6 in [ADR 0011](0011-course-test-scope-layers.md)):

- Infrastructure faults → **Library tier** (exception propagates; trace may show a partial run).
- Application markers → remain **Observe tier** unless egress boundary is implemented.

This decision is currently in effect in production/dev workflow.

## Consequences

- Agents and review cite ADR 0012 for runtime reaction semantics.
- Module READMEs and `graphtrace.ipynb` point here; placeholder “round 2” policy is superseded by this ADR’s boundary section (deferred implementation).
- L6 chaos **tests** remain optional until an exemplar is added; runtime expectations are defined here.
