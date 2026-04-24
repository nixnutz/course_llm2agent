# 0003 - Require ADR Check in Plan Creation

- Status: Accepted
- Date: 2026-04-24
- OverheadSeconds: 0

## Context

ADR updates were missed in some larger changes because guidance existed in docs, but was not consistently enforced during planning.

## Decision

Introduce an always-applied Cursor rule that requires an explicit ADR relevance check for every plan:
- If ADR-relevant, include concrete ADR follow-up tasks in the plan.
- If not ADR-relevant, include a short rationale in the plan.
- Treat portable runtime control surface changes as ADR-relevant, even when the diff is runtime-settings-only.
- Use a hybrid follow-up by default: append `raw-log` entry always, and add full ADR when a stable contract/invariant is introduced or changed.

Rule file:
- `.cursor/rules/adr-plan-check.mdc`

## Consequences

- Planning becomes explicit and auditable regarding ADR obligations.
- Fewer missed ADR updates for high-impact changes.
- Slightly more overhead per plan (one mandatory decision point).
