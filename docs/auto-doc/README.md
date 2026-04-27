# Auto-Doc (Experiment)

Goal: Continuously capture project context so reviews include not only the latest diff, but also the timeline and rationale.

## Idea

- `a) User stories / user value`: What improved for whom, and with which observed effect?
- `b) Architecture / invariants`: Which stable structural decisions are in force? (currently paused)
- `c) Implementation / discussions`: Which concrete decisions were made during implementation?

## Current Scope

- User value log active: `docs/auto-doc/value/user-value-log.md`
- Implementation/decision tracking active:
  - Raw log: `docs/auto-doc/adr/raw-log.md`
  - Summarized ADRs: `docs/auto-doc/adr/`
  - Current operational decisions:
    - `docs/auto-doc/adr/0004-local-ollama-overload-guardrails.md`
    - `docs/auto-doc/adr/0005-define-ollama-runtime-control-surface.md`
- Architecture/invariants track (`b`) is currently inactive because no clear need has appeared so far.

## Use in Review

- Before review: collect and condense relevant log entries.
- In review: provide the compact timeline as context (not only the latest state).
- After review: feed open points/decisions back into ongoing logging.
- Optional post-commit review tracking can use local branch status in `docs/internal/review-status.md` (local-only, gitignored).
- The review output should include explicit documentation status for `raw-log`, `ADR file`, and `user-value log`.
- The local review status file can persist these doc decisions/status values to avoid context-loss after user clarifications.

## Rules vs Hooks (ADR guardrails)

- Rules decide semantics: whether ADR/raw-log updates are needed.
- Hooks enforce mechanics (warn-only): append-only raw-log, raw-log line format, ADR required fields/sentence.
- Hook files:
  - `.cursor/hooks.json`
  - `.cursor/hooks/adr_guardrails.py`
- Rollout mode: warn-only first; promote selected checks to blocking only after team validation.

## Principle

- Minimal overhead, high context value.
- No prose: short, concrete, traceable entries.

For ADR experiment limitations and required explicit request behavior, see `docs/internal/adr-experiment-notes.md`.
