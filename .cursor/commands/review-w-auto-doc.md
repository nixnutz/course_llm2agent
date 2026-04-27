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
4. Commit readiness gate

If there are no issues, explicitly say: "No issues found."

## Scope and Intent

- Keep the review lightweight and practical.
- Prioritize correctness, regressions, and test gaps.
- Avoid over-process for trivial playground/notebook updates.

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
- User value log: `add` | `skip (trivial)` | `update existing`

When proposing `skip (trivial)`, include one short justification, e.g.:
"Change is a local notebook playground tweak with no durable architectural or user-value impact."

## If Auto-Doc Is Not Skipped

Propose exactly one candidate line for each file:

- `docs/auto-doc/adr/raw-log.md`
- `docs/auto-doc/value/user-value-log.md`

Keep entries concise and concrete.

For post-commit mode, aggregate auto-doc decision across selected commit range/group.

## Commit Readiness Gate (Mandatory)

Return:

- `findings_resolved: yes/no`
- `doc_decisions_made: yes/no`
- `ready_to_commit: yes/no`

Use `doc_decisions_made: yes` even when both logs are intentionally skipped as trivial.

When review is post-commit only (clean working tree), `ready_to_commit` may be `n/a`.
