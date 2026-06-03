# Placeholder allowlist audit (course sketch)

Deterministic check that LLM outputs only use **`E{n}_{salt}` tokens issued for this
session**. Subgraph state carries ``PlaceholderAllowlist`` (token strings only) — never
raw email addresses.

## What we catch

| Case | Example | Result |
|------|---------|--------|
| Allowed token | `E0_a1b2c3d4` in allowlist, appears in output | OK |
| Invented index | `E99_a1b2c3d4` when allowlist has E0,E1 only | `placeholder_violation` log |
| Wrong salt | `E0_cafebabe` when session salt is `a1b2c3d4` | `placeholder_violation` log |
| Truncated but still placeholder-like | `E0_a1b2c3` vs allowed `E0_a1b2c3d4` | `placeholder_violation` log (not an exact allowlist match) |
| `UNKNOWN` in `who` | literal string, not placeholder-like | OK |

## Known limitations (document + test)

| Limitation | Example | Test |
|------------|---------|------|
| Shape breaks regex (not detected) | `E0-a1b2c3d4` (hyphen, not `_`) vs allowed `E0_a1b2c3d4` | `test_malformed_separator_not_reported` |
| Input recall not checked | Input has E0+E1, output only E0 | deferred (round 2) |
| Failure policy undecided | violation logged, output still merged | round 2 |

Direct ``get_todo_list_node()`` / smoke invokes **bypass** subgraph audit — use compiled
subgraph or parent bridge for allowlist enforcement.

## Round 2 (separate)

Reaction when ``unknown_tokens`` is non-empty (soft/hard/strip/block demask).

## References

- Bridge derives allowlist: ``allowlist_from_pii_email`` in ``allowlist.py``
- ADR: ``docs/auto-doc/adr/0009-pii-email-masking-pipeline.md``
