# Editor and Agent Workflow

Contributor conventions for Cursor, VS Code, and repo agents — not the learner quickstart.
First-time lab setup: [getting-started.md](getting-started.md).

## Execution Model

- Cursor runs on the host machine.
- `<repo>/src/` is bind-mounted to `/workspace/src/` in the `dev` container (same files on
  host and in kernels).
- Code-related commands should run through `container/compose/scripts/dev/cmd.sh`.
- Use `container/compose/scripts/dev/session.sh` only for explicit interactive diagnostics.
- Do not rely on shell state between `dev-cmd` calls.
- From the repository root, `make ruff-check` runs `ruff check` (no fixes) and `make ruff` runs `ruff check --fix` plus `ruff format` in `/workspace/src` via the dev wrapper. Jupyter notebooks (`*.ipynb`) are excluded in `src/pyproject.toml`.
- With `make up`, JupyterLab in `dev` is reachable from the host — default URL in
  [getting-started §7](getting-started.md#7-services-with-a-web-ui). See
  `container/dev-image/README.md` → **Notebook Mode** for restart/rebuild.
  In Cursor or VS Code, use **Specify Jupyter Server for Connections** → that URL so kernels inherit
  `MODEL_API_KEY_*` and TLS trust from `dev`; a host-local Python kernel on the mounted `src/` tree
  does not get those variables.

## Scope and Language

- Use host shell primarily for repository operations (for example git, file moves, docs edits).
- Write all source code and all documentation in English.

## Rule Source of Truth

- Agent behavior is enforced via `.cursor/rules/`.
- `.cursor/rules/` is the normative source for agent behavior.
- This document explains the workflow for humans; if there is any conflict, rules win.

## Plan Creation ADR Check

When creating or updating an implementation plan, always perform an explicit ADR update check:

- `Does this change require ADR update?`
- If yes: include concrete ADR follow-up tasks in the plan (raw-log append and/or new ADR file).
- If no: add one short rationale line in the plan.

Treat a change as ADR-relevant when it defines or changes a portable runtime control surface, even if the diff only touches runtime settings. Typical examples are centrally managed operational knobs (debug, queue, concurrency, max loaded models, timeout budgets) that should remain controllable across orchestrators (Compose, Kubernetes).

Use the hybrid ADR workflow by default:

- Always add one short `docs/auto-doc/adr/raw-log.md` entry for ADR-relevant changes.
- Add a dedicated ADR file when a stable contract/invariant is introduced or changed.
