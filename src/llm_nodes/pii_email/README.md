# PII email node (course sketch)

This package demonstrates **architecture**, not production-grade PII handling.
The split (LLM detection → deterministic Python mask → trusted restore) is the
learning goal; edge cases are documented and only lightly guarded.

## What is in scope here

- **Forward mask** (`mask.py`): position-based splicing, cursor for repeated
  identical `span` strings, soft-fail log markers.
- **Restore** (`demask_pii_emails`): exact placeholder → email replace when
  tokens are intact.
- **Tests**: unit tests for the deterministic path; LLM recall via eval under
  `tests_and_evals/evals/llm_nodes/pii_email/`.

## Known limitations (accepted for the course)

| Area | Behavior today | If it breaks |
|------|----------------|--------------|
| **Detection recall** | Python trusts LLM `occurrences`. Too few entries for duplicate spans masks only the first match; leftover text triggers `leak_suspected`. JSON order of identical spans does not matter (cursor + sort by position). | Check logs; fix prompt/eval recall — not auto-repair in `mask.py`. |
| **Downstream LLM nodes** | After each TODO subgraph LLM step, ``placeholder_audit`` checks tokens against ``PlaceholderAllowlist`` (bridge-derived, no raw emails). | See ``placeholder_audit/README.md``; Observe tier today ([ADR 0012](../../../docs/auto-doc/adr/0012-course-error-mode-contract.md)). |
| **Restore** | `demask_pii_emails` uses exact `.replace`; no fuzzy match. | Broken or invented tokens stay in output. |

Do not treat warnings (`leak_suspected`, `span_not_found`, …) as sufficient for
production compliance; they exist so you can see KI-Schlampigkeit during labs.

## References

- ADR: `docs/auto-doc/adr/0009-pii-email-masking-pipeline.md`
- Error-mode contract: `docs/auto-doc/adr/0012-course-error-mode-contract.md`
- Post-LLM audit: `src/llm_nodes/placeholder_audit/README.md`
- Module contract: docstring at top of `mask.py`
