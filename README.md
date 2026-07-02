# Toolbert Lab - a home for a tiny agent

This is an independent, single-person project built from scratch for the [OpenCampus.sh](https://www.opencampus.sh/) course [*From LLMs to Agents*](https://edu.opencampus.sh/course/632) — the course mandated no starter template or framework, so the architecture, infrastructure, and tooling choices (LangGraph, the Compose stack, the Sysbox sandbox) are my own. OpenCampus is a non-profit organization working in close collaboration with local universities. ECTS-Credits are granted for some of their projects.

[![Course presentation](docs/toolbert_lab.png)](docs/toolbert_lab.pdf)

**[Open full presentation (PDF)](docs/toolbert_lab.pdf)** — course summary (sessions 1–8).

Course deliverable: **sessions 1–8** (session 8 is a rough end-to-end demo). This repository
continues for experiments (**session 9+**).

## Why this lab?

Agents need a **home and supervision** — like kids at play, but for LLM graphs. Toolbert Lab is
that home: a local Compose stack where you develop LangGraph agents in notebooks while
infrastructure handles models, tracing, chaos testing, and (eventually) sandboxed tool execution.

Supervision here is concrete: state boundaries, deterministic guards, tracing, and sandboxed
tool execution — the mechanics you need once an LLM stops being a chatbot and starts touching
data and tools. The [presentation PDF](docs/toolbert_lab.pdf) and session notebooks carry the
full narrative; this repo is the runnable lab archive. The next section shows what that focus
looks like in practice.

## Tiny agent, large engineering surface

**The agent task is deliberately trivial** — a frontier model would do it in a single prompt:
mask email PII → extract TODOs → format as Markdown → demask. That is the whole point.
Shrinking the *task* to almost nothing keeps the focus on the *mechanics* the presentation
asks about: where are the contracts and boundaries? What flows through global state? What can
a tool node actually see and do?

```mermaid
flowchart LR
  START --> pii_extract_node
  pii_extract_node --> todo_extract_node
  todo_extract_node --> todo_markdown_node
  todo_markdown_node --> demask_node
  demask_node --> END
```

The top-level graph stays small **on purpose**. The engineering lives in the boundaries,
guards, and infrastructure around it:

| Concern | How the lab handles it |
|---------|------------------------|
| **State & privacy boundaries** | TODO extraction runs in a *need-to-know* subgraph — it sees masked text and a placeholder allowlist, never raw PII |
| **Deterministic guards** | Pydantic-typed state, PII-leak checks, placeholder audit after each LLM step (the LLM proposes, Python verifies) |
| **Trusted demask** | A deterministic code path restores placeholders only in `final_result`, never in intermediate fields |
| **Observability** | Reducer hooks + LiteLLM per-call logs + Phoenix span tree — every state transition is auditable |
| **Tool sandboxing** | The bash tool runs in a Sysbox HTTP-bridged sandbox (sessions 7–8): isolation, timeouts, cleanup — a lab prototype, not production security |
| **Chaos testing** | A clean vs. Toxiproxy chaos channel injects latency, timeouts, and provider faults |

Every run is traced end-to-end, so those guards and boundaries are visible in practice:

![Phoenix trace of a parent-graph run](src/assorted/session5/trace_example.png)

Full story: [presentation (PDF)](docs/toolbert_lab.pdf) · pipeline map:
[pipeline and nodes](docs/course/pipeline-and-nodes.md) · rationale:
[engineering decisions](#engineering-decisions).

## Course sessions (1–8)

| Session | Focus | Notebooks |
|---------|--------|-----------|
| 1 | Chaos channel (Toxiproxy), home assignment | [`chaos.ipynb`](src/assorted/session1/chaos.ipynb), [`homeassignment.ipynb`](src/assorted/session1/homeassignment.ipynb) |
| 2 | RAG basics (vector search in the lab) | [`rag_basics.ipynb`](src/assorted/session2/rag_basics.ipynb), [`rag_pgvector.ipynb`](src/assorted/session2/rag_pgvector.ipynb) |
| 3 | LangGraph basics, message reducer | [`langgraph.ipynb`](src/assorted/session3/langgraph.ipynb), [`langgraph_messages.ipynb`](src/assorted/session3/langgraph_messages.ipynb) |
| 4 | Parent graph assembly (PII → TODO → demask) | [`langgraph.ipynb`](src/assorted/session4/langgraph.ipynb) |
| 5 | Phoenix tracing, reducer observability | [`graphtrace.ipynb`](src/assorted/session5/graphtrace.ipynb) |
| 6 | Tool subgraph with safe mock tool | [`tool_node_basics.ipynb`](src/assorted/session6/tool_node_basics.ipynb) |
| 7 | Sandbox infrastructure (Sysbox HTTP API) | [`tool_node_sysbox.ipynb`](src/assorted/session7/tool_node_sysbox.ipynb) |
| 8 | End-to-end parent graph (rough) — Sysbox + in-graph demask | [`presentation.ipynb`](src/assorted/session8/presentation.ipynb) |

Full notebook index: [`src/assorted/README.md`](src/assorted/README.md).

## Lab and documentation

- [Getting started](docs/getting-started.md) — start the agent lab, first Python exercise in `dev`
- [Course pipeline and nodes](docs/course/pipeline-and-nodes.md) — parent-graph sketch and modules
- [Error handling (course)](docs/course/error-handling.md) — Guard / Observe / Library
- [Editor and agent workflow](docs/editor-and-agent-workflow.md) — Cursor, dev-cmd, contributors
- [Compose stack](container/compose/README.md) — runtime, env, chaos channel
- [Full documentation index](docs/README.md)

## Engineering decisions

Key choices are recorded as short [ADRs](docs/auto-doc/adr/README.md) — for example the
[PII masking pipeline](docs/auto-doc/adr/0009-pii-email-masking-pipeline.md), the
[course error-mode contract](docs/auto-doc/adr/0012-course-error-mode-contract.md), and the
[Sysbox sandbox HTTP API](docs/auto-doc/adr/0015-sysbox-bash-sandbox-http-api.md).

Note: the full implementation plans are **not** in this repository. The ADRs are kept
deliberately short — a lightweight side experiment in decision logging, not full design docs.

## Tests and scope

A layered pytest suite (unit → mocked parent-graph E2E → Toxiproxy chaos) lives under
[`src/tests_and_evals`](src/tests_and_evals/README.md) — reminders and smoke checks, not
exhaustive coverage. Run it inside the `dev` container.

**Deliberate non-goals.** This is a course lab (~5 ECTS, roughly a 125 h budget), and the
scope was set on purpose: **no CI**, no CONTRIBUTING, no production hardening. It is an
*agent* course where the interesting problems turned out to be the engineering *around* the
agent — so the depth went into state boundaries, guards, sandboxing, and observability rather
than agent breadth or a polished use case. CI, richer evals, and monitoring are natural next
steps, not part of this deliverable.

## Beyond the course (session 9+)

Follow-up experiments and ad-hoc notebooks may appear under `src/assorted/` without being part of the course deliverable (sessions 1–8).

## Course description (OpenCampus.sh)

> Adapted from the OpenCampus.sh course *From LLM to Agents* (instructor: [Henrik Horst](https://opencampus.sh)).  
> This repository is an independent lab archive maintained by Ulf Wendel — not the official course repository. The course contributed concepts and a few minimal examples; the code, design, and infrastructure here are original to this repo.

### What you get

Ramp-up course for the new fascinating capabilities of LLMs and the emerging applications of AI Agents with LLMs as the control center.

### Paths

Throughout the course we will build multiple different applications on different levels of difficulty.

There are several tracks depending on your level of expertise:

"Taster" : You take the course only to get an overview grasp of the concepts

"Beginner": You do not have a lot of experience but want to build first prototypes

"Intermediate": You want to level up your already existing skills and knowledge

"Expert": You really want to deep dive in the materials both from practical as from a theoretical perspective

You can choose the path you want to take, so that the course is open for everybody interested in the topic. We achieve those different paths with more and more in depth learning materials and tasks for the more advanced paths. You are free to choose your path and change it during the semester

### About the course instructor

Henrik Horst teaches Machine Learning courses at opencampus.sh since 5 years. Also he is a Generative AI course instructor at the Helmholtz Gesellschaft and the Wirtschaftsakademie Schleswig-Holstein. He works as CEO at WikiMind GmbH, an AI-Software company, and has carried out multiple AI projects there.

### Guest speakers

There will be during the course some guest speakers invited to talk about their life as an AI engineer

### What you should bring

Basic Programming Knowledge in Python!!

A prerequisite is Python skills, if you are lacking those first take the course: Python Programming: Beginner to Practitioner

Otherwise that is all for the "Taster" and "Beginner" path. For the more advanced paths more programming and project experience is necessary and also familiarity with different software tools like git and docker.

## License

Copyright 2026 Ulf Wendel. Licensed under the Apache License 2.0 — see [LICENSE](LICENSE).

Repository code, docs, and lab materials: Apache 2.0 (see LICENSE).  
The course description section above is third-party course marketing text from OpenCampus.sh.
