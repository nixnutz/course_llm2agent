# ADR Experiment Notes

## Status

This repository uses an always-applied planning rule for ADR relevance checks.

## Important Limitation

ADR updates are still not automatic for every change because implementation can proceed without adding ADR artifacts unless explicitly triggered by the rule decision or by user request.

## Plan sidecar (optional)

- For one-off Plan-mode context outside the repo, use `docs/internal/adr-plan-sidecar.md` (see `adr-plan-sidecar.template.md`).
- Overwrite per feature; not committed. Agents use it during review and ADR drafting; implementation state in the sidecar must match reality.

## Required User Behavior

If you want an ADR update for a change, explicitly request it in chat every time.

Recommended phrase:

`Please add/update ADR entries for this change.`

## Runtime Control Surface Clarification

Even "runtime-settings-only" changes should be treated as ADR-relevant when they define or change a portable control surface (for example debug, queue, concurrency, max loaded models, timeout knobs expected to map from Compose to Kubernetes later).
