---
name: review-w-auto-doc
description: Run a short formal review with optional auto-doc skip for trivial changes
---

Review the current repository changes (staged + unstaged) with a short, formal workflow.

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

## Commit Readiness Gate (Mandatory)

Return:

- `findings_resolved: yes/no`
- `doc_decisions_made: yes/no`
- `ready_to_commit: yes/no`

Use `doc_decisions_made: yes` even when both logs are intentionally skipped as trivial.
