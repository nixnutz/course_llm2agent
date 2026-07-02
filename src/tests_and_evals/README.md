## tests_and_evals

This area is intentionally an infrastructure sketch, not a complete testing platform.
It is optimized for a single-developer workflow and local LLM usage. Parent-graph tests
exercise the **course reference** `build_parent_base_graph()` sketch — reminders and smoke
checks, not a frozen product contract.

**Normative test scope:** [ADR 0011](../../docs/auto-doc/adr/0011-course-test-scope-layers.md) (six layers; tests are reminders, not exhaustive coverage).

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
- chaos (L6, stack up): `pytest src/tests_and_evals/tests -m "chaos" -v` — two serial tests (segments A/B); requires documented env from `container/compose/.env.example` (`MODEL_API_KEY_DEV` via keys export, `MODEL_BASE_URL_CHAOS`, `TOXIPROXY_URL`); Toxiproxy proxies (`make toxiproxy-bootstrap` if chaos channel returns 502); smoke/chaos model is the fixed course default in `common/fixtures.py` (`SMOKE_MODEL`), not an env var; do not combine with `pytest -n` unless `xdist_group("chaos")` is acceptable
- eval: `pytest src/tests_and_evals/evals -m "eval"`

Eval execution is intentionally manual via explicit command selection.
