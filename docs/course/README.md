# Course implementation docs

Learner- and implementer-facing notes for the code under `src/` (not the official
OpenCampus.sh syllabus). Reference for the **course deliverable (sessions 1–8)** — session 8 is
still rough; a teaching lab archive, not a shipped agent product or frozen API.

Start with [getting started](../getting-started.md) if the local stack is not up yet.  
Course narrative: [presentation PDF](../toolbert_lab.pdf).

## Topics

| Doc | What it covers |
|-----|----------------|
| [Pipeline and nodes](pipeline-and-nodes.md) | Parent-graph sketch, bridges, module map, notebooks, tests |
| [Error handling](error-handling.md) | Guard / Observe / Library tiers (Mode C) and where to look in code |

## Code and notebooks

| Area | Location |
|------|----------|
| Parent graph sketch | `src/graphs/parent_base_graph.py` — `build_parent_base_graph()` |
| Course notebooks | `src/assorted/` — see [session README](../../src/assorted/README.md) |
| PII + masking | `src/llm_nodes/pii_email/README.md` |
| Placeholder audit | `src/llm_nodes/placeholder_audit/README.md` |
| Message reducer | `src/reducer/__init__.py` (module docstring) |
| Tests by layer | `src/tests_and_evals/README.md` |

## Normative decisions (experiment)

Stable contracts are summarized as ADRs under `docs/auto-doc/adr/`. Course-relevant
examples:

- [0012 — error-mode contract](../auto-doc/adr/0012-course-error-mode-contract.md)
- [0009 — PII email masking pipeline](../auto-doc/adr/0009-pii-email-masking-pipeline.md)
- [0011 — test scope layers](../auto-doc/adr/0011-course-test-scope-layers.md)
- [0006 — toxiproxy chaos channel](../auto-doc/adr/0006-toxiproxy-chaos-channel-architecture.md)
