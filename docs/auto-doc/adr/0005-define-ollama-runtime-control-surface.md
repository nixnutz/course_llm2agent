# 0005 - Define Ollama Runtime Control Surface

- Status: Accepted
- Date: 2026-04-24
- OverheadSeconds: 0

## Context

Recent tuning work changed only runtime settings, but introduced an operational requirement that should remain portable:
important Ollama runtime knobs must be centrally managed and transferable across orchestrators.

Without an explicit contract, these controls stay implicit in Compose files and are easy to lose during migration
(for example Compose to Kubernetes).

## Decision

Define a stable runtime control surface for local Ollama operations in this repository:

- `OLLAMA_DEBUG`
- `OLLAMA_NUM_PARALLEL`
- `OLLAMA_MAX_QUEUE`
- `OLLAMA_MAX_LOADED_MODELS`

These knobs are treated as centrally managed operator controls and should be preserved when mapping runtime config
to future deployment targets.

This decision does not change model selection (`OLLAMA_MODELS`) or keep-alive behavior (`OLLAMA_KEEP_ALIVE`) in this step.

## Consequences

- Runtime tuning intent is explicit, reviewable, and less likely to regress.
- Future orchestrator migration has a documented minimum config contract for Ollama runtime behavior.
- Planning guidance now treats portable runtime-control changes as ADR-relevant, even for small "settings-only" diffs.
