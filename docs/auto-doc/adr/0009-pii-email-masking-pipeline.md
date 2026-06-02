# 0009 - Split PII Email Masking into LLM Detection and Deterministic Python Pipeline

- Status: Accepted
- Date: 2026-06-02
- OverheadSeconds: 0

## Context

The `pii_email` node originally let the LLM both detect emails and produce the masked text plus a deduplicated email list.
For inputs like `ulf.wendel at phpdoc.de, ulf.wendel@phpdoc.de` it was ambiguous which span a placeholder mapped to, dedupe was unverifiable, and the LLM could silently over- or under-redact the text it returned.
This made restore (placeholder -> email) error-prone and the behavior hard to test and audit.

## Decision

Split responsibilities along determinism boundaries:

- The LLM returns only `occurrences: [{span, raw}]` (verbatim span + its normalized form), in reading order, with no deduplication and no masked text.
- Deterministic Python (`src/llm_nodes/pii_email/mask.py`) builds the masked text by position-based splicing in the original input, assigns collision-free placeholders `E{n}_{salt}` (salt chosen so it does not occur in the input), deduplicates by `raw.strip().lower()` into `identities`, and keeps a per-span audit trail in `occurrences`.
- Soft-fail markers (pipeline never aborts): `span_not_found` (warning, raw discarded), `normalization_failed` (error, span still masked with `identity=None`), `leak_suspected` (warning).

The `PIIEmail` state carries `text`, `salt`, `identities`, and `occurrences`.
This decision is currently in effect in production/dev workflow.

## Consequences

- Masking, dedupe, and restore are deterministic and unit-testable without an LLM (`test_mask.py`).
- Placeholders cannot collide with original text, so restore via string replace is safe.
- PII is removed even when an email cannot be normalized (`identity=None`), trading restorability for safety.
- The LLM eval narrows to recall of `(span, raw)` detection; text integrity is checked separately against `forbidden_in_text`.
