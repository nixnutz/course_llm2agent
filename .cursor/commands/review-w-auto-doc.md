---
name: review-w-auto-doc
description: Run a short formal review with optional auto-doc skip for trivial changes
---

Run a short formal review with local review-state tracking.

Support both:
- working-tree review (staged + unstaged changes)
- post-commit review (commits since last local review state)

Use local state file (branch-scoped): `docs/internal/review-status.md`.
Do not use git tags/refs/notes for review tracking.

## Required Review Output

Return results in this exact section order:

1. Findings (by severity: High, Medium, Low)
2. Open questions / assumptions
3. Auto-doc decision
4. Documentation status gate
5. Commit readiness gate

If there are no issues, explicitly say: "No issues found."

Numbering contract (mandatory):
- Findings must use IDs: `F1`, `F2`, ...; optional subpoints may use `F1.1`, `F1.2`, ...
- Open questions must use IDs: `O1`, `O2`, ...
- Assumptions must use IDs: `A1`, `A2`, ...
- IDs must be unique within one review response.
- If a category has no items, output `none` for that category.
- In section 2, always split output into two labeled blocks:
  - `Open questions` (O-items)
  - `Assumptions` (A-items)

Example style (minimal):
- Findings: `F1: Potential regression in timeout handling.`
- Open questions: `O1: Should this cover post-commit mode too?`
- Assumptions: `A1: Notebook output churn is intentional for this run.`

## Scope and Intent

- Keep the review lightweight and practical.
- Prioritize correctness, regressions, and test gaps.
- Avoid over-process for trivial playground/notebook updates.
- Use skip memory to suppress accepted recurring review noise when configured.

## Review Skips Memory (Mandatory)

Use local skip memory file: `docs/internal/review-skips.md`.

At the beginning of every run:

1) Read skip entries from `docs/internal/review-skips.md` (if file exists).
2) Apply matching entries silently to Findings, Open questions, and Assumptions.
3) Track how many items were filtered by skips.

At the end of every run, include:

- `applied_review_skips: N`

Skip entry contract:

- Format: `R-### | scope | pattern | rationale | added_at`
- FIFO cap: keep at most 10 entries (drop oldest when adding entry 11+).
- Keep matching practical and conservative; do not hide high-risk regressions.

When user explicitly requests permanence (for example, "always ignore this" / "never ask this again"):

1) Propose exactly one candidate skip entry line.
2) Ask for explicit confirmation before writing the entry.
3) On confirmation, append entry and enforce FIFO cap.
4) Reflect applied skip count on subsequent reviews.

## Local Review-State Flow (Mandatory)

At the beginning of every run:

1) Detect current branch and read `docs/internal/review-status.md` for this branch.
2) If no branch status exists and branch already has commits, ask:
   - A) start from latest commit only
   - B) start from branch start
3) If there are commits since last reviewed point, show:
   - count of pending commits
   - oldest 3 commit headlines (one-line short summary)
4) Ask what to do:
   - A) mark all pending commits as already handled, continue with current working-tree review
   - B) review pending commits now (single commit, range, or logical group)
5) Update `docs/internal/review-status.md` according to the chosen path.

Use AskQuestion for these user choices.

## Auto-Doc Decision (Mandatory)

Always include an explicit decision for both logs:

- ADR raw log: `add` | `skip (trivial)` | `update existing`
- ADR file: `add` | `skip (trivial)` | `update existing`
- User value log: `add` | `skip (trivial)` | `update existing`

When proposing `skip (trivial)`, include one short justification, e.g.:
"Change is a local notebook playground tweak with no durable architectural or user-value impact."

Hard gate: the review is not complete until all three decisions are explicit.

## If Auto-Doc Is Not Skipped

Propose exactly one candidate line for each log file:

- `docs/auto-doc/adr/raw-log.md`
- `docs/auto-doc/value/user-value-log.md`

Keep entries concise and concrete.

For post-commit mode, aggregate auto-doc decision across selected commit range/group.

If ADR file decision is `add` or `update existing`, include:
- target file path under `docs/auto-doc/adr/`
- one-sentence ADR intent summary

## Documentation Status Gate (Mandatory)

Return:

- `raw_log_status: done|pending|n/a`
- `adr_file_status: done|pending|n/a`
- `user_value_log_status: done|pending|n/a`
- `applied_review_skips: <number>`

Rules:
- `done`: decision made and required edit/candidate provided
- `pending`: review identified required follow-up not yet prepared
- `n/a`: explicitly skipped as trivial with justification

## Commit Readiness Gate (Mandatory)

Return:

- `findings_resolved: yes/no`
- `doc_decisions_made: yes/no`
- `ready_to_commit: yes/no`

Use `doc_decisions_made: yes` even when both logs are intentionally skipped as trivial.

Set `doc_decisions_made: no` if any of the three auto-doc decisions is missing or any documentation status is `pending`.

When review is post-commit only (clean working tree), `ready_to_commit` may be `n/a`.
