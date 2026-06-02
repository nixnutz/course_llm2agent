# ADR Plan Sidecar (local, one-off)

Copy to `docs/internal/adr-plan-sidecar.md` (gitignored). Overwrite when starting a new feature; trim after review.

```md
## context
- date: YYYY-MM-DD
- feature_or_change: <short title>
- branch: <optional>

## adr_relevant_bullets
- decision_intent: <what we decided and why>
- constraints: <limits, env, compatibility>
- alternatives_rejected: <what we did not do>
- runtime_control_surface: yes|no — <note if yes>

## implementation_state
- state: implemented | partial | proposal
- evidence: <tests, paths, or "not yet">

## adr_hint
- hint: raw-log-only | new-adr | none
- no_adr_rationale: <required when hint is none>

## open_for_review
- <optional bullets the review should resolve>
```
