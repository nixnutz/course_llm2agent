# Review Skips Memory

Purpose: keep a tiny, practical memory of accepted recurring review skips to reduce repeated noise.

## Contract

- Single skip level only (no hardness levels).
- Entries are silently applied by review flow.
- FIFO cap: `MAX_ENTRIES = 10`.
- Append new entries at the bottom.
- If adding a new entry would exceed 10 entries, remove the oldest entry first.

## Entry Format

One line per entry:

`R-### | scope | pattern | rationale | added_at`

Example:

`R-001 | notebooks | notebook output churn | accepted as didactic | 2026-04-30`

## Entries

`R-001 | global | cursor-profile-repair.sh untracked | unrelated local tooling; exclude from commit reviews | 2026-06-05`

Guidance:

- Keep entries short and concrete.
- Use stable wording in `pattern` so matching is predictable.
- Prefer scope values such as `notebooks`, `docs`, `compose`, `global`.

