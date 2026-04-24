# Editor and Agent Workflow

This document captures editor, Cursor, and agent-specific conventions for this repository.

## Execution Model

- Cursor runs on the host machine.
- Source code is mounted into the running `dev` container.
- Code-related commands should run through `container/compose/scripts/dev-cmd.sh`.
- Use `container/compose/scripts/dev-session.sh` only for explicit interactive diagnostics.
- Do not rely on shell state between `dev-cmd` calls.

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
