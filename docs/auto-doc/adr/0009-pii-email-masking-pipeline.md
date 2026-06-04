# 0009 - Split PII Email Masking into LLM Detection and Deterministic Python Pipeline

- Status: Accepted
- Date: 2026-06-02
- Amended: 2026-06-04 (PII-in-graph compromise; parent `demask_node`)
- OverheadSeconds: 0

## Context

The `pii_email` node originally let the LLM both detect emails and produce the masked text plus a deduplicated email list.
For inputs like `ulf.wendel at phpdoc.de, ulf.wendel@phpdoc.de` it was ambiguous which span a placeholder mapped to, dedupe was unverifiable, and the LLM could silently over- or under-redact the text it returned.
This made restore (placeholder -> email) error-prone and the behavior hard to test and audit.

The implementation in this repository is a **course teaching sketch** (architecture and determinism boundaries), not production-grade PII compliance tooling; see Known limitations below.

## Decision

Split responsibilities along determinism boundaries:

- The LLM returns only `occurrences: [{span, raw}]` (verbatim span + its normalized form), in reading order, with no deduplication and no masked text.
- Deterministic Python (`src/llm_nodes/pii_email/mask.py`) builds the masked text by position-based splicing in the original input, assigns collision-free placeholders `E{n}_{salt}` (salt chosen so it does not occur in the input), deduplicates by `raw.strip().lower()` into `emails`, and keeps a per-span audit trail in `occurrences` (`Occurrence.email` is the mail-ready address per span).
- Soft-fail markers (pipeline never aborts): `span_not_found` (warning, raw discarded), `normalization_failed` (error, span still masked with `email=None`), `leak_suspected` (warning).
- After each TODO subgraph LLM step, deterministic `placeholder_audit` checks output strings against a bridge-derived `PlaceholderAllowlist` (token strings only, no raw emails in subgraph state); round 1 logs `placeholder_violation` on unknown tokens (reaction policy deferred).
- **Restore (demask):** deterministic `demask_pii_emails(masked_text, pii)` runs only in **trusted** code — never in TODO subgraph LLM nodes. Session 5+ may call it from a parent-graph `demask_node` (no LLM) so Phoenix/reducer see one span per step; Session 4 may still demask in notebook code after `ainvoke`. Restore target in the course pipeline is **`todo_markdown.markdown`** only (not structured `todo_list` fields).

The `PIIEmail` state carries `text`, `salt`, `emails`, and `occurrences`.

### PII in the graph (course compromise)

**Ideal:** mask and demask at a dedicated **system boundary** with a narrow API; raw emails never live in LangGraph state.

**Why PII appears in-graph anyway:** masking requires reading human input once; `pii_email` (including `emails` for restore) must exist on `GlobalState` for that step. TODO subgraphs stay isolated via bridges — they do not receive raw emails.

**Accepted compromise (Session 5+):** trusted **parent** nodes only: `pii_extract_node` (mask) and `demask_node` (restore markdown). Untrusted LLM nodes never see `PIIEmail.emails`.

**If PII is in graph state, these rules apply:**

1. Raw emails only on `GlobalState.pii_email` — not in subgraph state or LLM prompts.
2. Mask before any external/untrusted LLM; demask only in trusted deterministic nodes or equally trusted app code.
3. No fuzzy or LLM-driven restore; use `demask_pii_emails` only.
4. Prefer observability without widening trust: in-graph demask is for trace trees, not a production boundary.

**Future optimum:** explicit ingress/egress API (mask in, demask out) with the compiled graph operating only on placeholders.
Here, *production/dev workflow* means this repository's course labs, tests, and session graphs—not a production PII compliance deployment.
This decision is currently in effect in production/dev workflow.

## Consequences

- Masking, dedupe, and restore are deterministic and unit-testable without an LLM (`test_mask.py`).
- Placeholders cannot collide with original text, so restore via string replace is safe when placeholders in the text are exact and intact.
- PII is removed even when an email cannot be normalized (`email=None`), trading restorability for safety.
- The LLM eval narrows to recall of `(span, raw)` detection; text integrity is checked separately against `forbidden_spans`.

## Known limitations (course scope)

This pipeline is a teaching sketch, not production compliance tooling. Documented gaps:

- **Under-reported duplicates:** if the LLM omits a repeated identical `span`, Python masks only occurrences consumed by the list; residual text raises `leak_suspected` (warning only).
- **Downstream placeholder audit:** invented/wrong-salt tokens (e.g. `E0_cafebabe` vs session salt) and truncated-but-still-matching tokens (e.g. `E0_a1b2c3` vs allowed `E0_a1b2c3d4`) log `placeholder_violation`; tokens that break the finder shape (e.g. `E0-a1b2c3d4`) are not detected — see `src/llm_nodes/placeholder_audit/README.md`. Input recall and failure policy are deferred.
- **`demask_pii_emails`** still uses exact `.replace`; it does not repair invalid tokens.
- See `src/llm_nodes/pii_email/README.md` for the maintainer-facing table.
