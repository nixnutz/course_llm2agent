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
- Architecture/invariants track (`b`) is currently inactive because no clear need has appeared so far.

## Use in Review

- Before review: collect and condense relevant log entries.
- In review: provide the compact timeline as context (not only the latest state).
- After review: feed open points/decisions back into ongoing logging.

## Principle

- Minimal overhead, high context value.
- No prose: short, concrete, traceable entries.

For ADR experiment limitations and required explicit request behavior, see `docs/internal/adr-experiment-notes.md`.
