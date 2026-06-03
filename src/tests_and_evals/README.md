## tests_and_evals

This area is intentionally an infrastructure sketch, not a complete testing platform.
It is optimized for a single-developer workflow and local LLM usage.

Current folder contract:
- `conftest.py`: registers shared fixtures via `pytest_plugins` (see `common/fixtures.py`)
- `common/`: minimal shared fixtures/utilities
- `tests/`: classic tests (current subtree preserved)
- `evals/`: manual golden-set/model-comparison checks
  - `evals/eval_collector.py`: shared per-session result store (`get_eval_collector`, xdist merge helpers). Node-neutral `EvalCaseResult` keyed by `suite` (the eval node), with `failed_checks` plus suite-specific `details` / `metrics`.
  - `evals/conftest.py`: eval-tree pytest hooks (reset collector, **per-suite** SHOULD gate); node tests live under `evals/llm_nodes/<node>/`

Direct pytest commands:
- fast: `pytest src/tests_and_evals/tests -m "not eval"`
- integration: `pytest src/tests_and_evals/tests -m "integration and not eval"`
- eval: `pytest src/tests_and_evals/evals -m "eval"`

Eval execution is intentionally manual via explicit command selection.
