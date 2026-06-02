## tests_and_evals

This area is intentionally an infrastructure sketch, not a complete testing platform.
It is optimized for a single-developer workflow and local LLM usage.

Current folder contract:
- `common/`: minimal shared fixtures/utilities
- `tests/`: classic tests (current subtree preserved)
- `evals/`: manual golden-set/model-comparison checks

Direct pytest commands:
- fast: `pytest src/tests_and_evals/tests -m "not eval"`
- integration: `pytest src/tests_and_evals/tests -m "integration and not eval"`
- eval: `pytest src/tests_and_evals/evals -m "eval"`

Eval execution is intentionally manual via explicit command selection.
