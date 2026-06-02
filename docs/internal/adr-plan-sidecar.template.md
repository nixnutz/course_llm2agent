# ADR Plan Sidecar (local, one-off)

Copy to `docs/internal/adr-plan-sidecar.md` (gitignored). Append one `## plan-<n>` block per finalized plan (see structure below); overwrite the whole file only when starting an unrelated feature. Do not auto-clear after review; only trim once ADR work for every captured plan is done and committed.

```md
## plan-<n>: <short title>

### context
- date: YYYY-MM-DD
- feature_or_change: <short title>
- branch: <optional>

### adr_relevant_bullets
- decision_intent: <what we decided and why>
- constraints: <limits, env, compatibility>
- alternatives_rejected: <what we did not do>
- runtime_control_surface: yes|no — <note if yes>

### implementation_state
- state: implemented | partial | proposal
- evidence: <tests, paths, or "not yet">

### adr_hint
- hint: raw-log-only | new-adr | none
- no_adr_rationale: <required when hint is none>

### open_for_review
- <optional bullets the review should resolve>
```

Repeat the `## plan-<n>` block (incrementing `<n>`) for each finalized plan; keep one shared trailing `## open_for_review` section only if you prefer aggregated review items.
