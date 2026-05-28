# 0008 - Enforce Strict LLM Node State and Two-Step TODO Flow

- Status: Accepted
- Date: 2026-05-28
- OverheadSeconds: 0

## Context

The session4 pipeline in `src/llm_nodes/` now coordinates multiple graph steps and shared state slices.
Without a strict shared state contract and clear TODO stage boundaries, accidental extra keys and mixed responsibilities can silently degrade behavior and learning examples.

## Decision

Use `BaseState` with `extra="forbid"` as the shared Pydantic base for LLM node states.
Keep TODO processing as two explicit stages: `todo_extract` for structured extraction and `todo_markdown` for markdown rendering.
This decision is currently in effect in production/dev workflow.

## Consequences

- State validation fails fast when unexpected fields appear.
- TODO extraction and markdown rendering can evolve independently.
- Session4 notebook flow reflects the same staged architecture used in code.
