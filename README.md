# OpenCampus.sh - From LLM to Agents

This repository is my scratchpad for the OpenCampus.sh course **"From LLM to Agents"**.

I use it to capture:
- quick notes from lessons
- experiments and mini-prototypes
- prompts, ideas, and TODOs
- mistakes, learnings, and follow-up questions

## Quickstart (5 minutes)

For a local, reproducible agent-dev setup with LiteLLM + Ollama:

```bash
cp container/compose/.env.example container/compose/.env
make up
make smoke-chat
```

Internal security note: from the `dev` container, backend services are reached via TLS through `caddy` (network-segmented compose setup).

Open LiteLLM UI:

```bash
xdg-open "https://localhost:4000/ui"
```

Open JupyterLab (course notebooks under `src/assorted`; stack must be up via `make up`). URL uses `HOST_BIND_IP`, `DEV_JUPYTER_PORT`, and `JUPYTER_TOKEN` from `container/compose/.env`:

```text
http://<HOST_BIND_IP>:<DEV_JUPYTER_PORT>/lab?token=<JUPYTER_TOKEN>
```

Details (in-container checks, restart after token change): `container/dev-image/README.md` → **Notebook Mode**.

If `smoke-chat` works, your local stack is ready for first agent experiments.

Builds and operational stack commands are available from the repository root via `Makefile`.
Compose internals stay in `container/compose`.
`make up` builds the dev runtime image automatically before starting compose.

## Workflow Notes

Editor, Cursor, and agent-specific workflow conventions are documented in:

- `docs/editor-and-agent-workflow.md`

TL;DR:
- Run code-related commands via `container/compose/scripts/dev/cmd.sh`.
- Write all source code and all documentation in English.

## ADR Note (Experimental)

ADR usage in this repository is experimental and currently treated as side learning.
It is intentionally separate from the official OpenCampus.sh course scope and materials.
Entry points:
- `docs/auto-doc/adr/README.md` for ADR conventions and summary format.
- `docs/auto-doc/adr/raw-log.md` for append-only decision collection during implementation.

## User Value Log (Experimental)

User value tracking is maintained as a lightweight, review-gated log.
Entry points:
- `docs/auto-doc/value/README.md` for process and format.
- `docs/auto-doc/value/user-value-log.md` for review entries.


## Original course description

### What you get

Ramp-up course for the new fascinating capabilities of LLMs and the emerging applications of AI Agents with LLMs as the control center.

### Paths

Throughout the course we will build multiple different applications on different levels of difficulty.

There are severel tracks depending on your level of expertise:

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

A prequisite is Python skills, if you are lacking those first take the course: Python Programming: Beginner to Practitionier

Otherwise that is all for the "Taster" and "Beginner" path. For the more advanced paths more programming and project experience is necessary and also familiarity with different software tools like git and docker.

## License

This project is licensed under the Apache License 2.0. See `LICENSE` for details.