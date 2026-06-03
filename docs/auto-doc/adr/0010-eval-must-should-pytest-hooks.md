# 0010 - Eval MUST/SHOULD Gating via Pytest Session Hooks

- Status: Accepted
- Date: 2026-06-03
- OverheadSeconds: 0

## Context

Golden-set evals mix hard requirements (MUST) with softer targets (SHOULD). Failing every SHOULD case inside the test function makes local LLM evals noisy; ignoring SHOULD entirely hides regressions. We also want one aggregated SHOULD pass rate per pytest run and compatibility with `pytest-xdist` without fixture-based session teardown.

## Decision

- Tests under `tests_and_evals/evals/` call `get_eval_collector()` inside each test function (never at module import), `record()` per case, and `assert` MUST failures in the test.
- `tests_and_evals/evals/conftest.py` resets the collector in `pytest_sessionstart`, merges worker results when xdist is active (`numprocesses` / `pytest_testnodedown`), and applies the SHOULD pass-rate gate **per suite** in `pytest_sessionfinish` (`SHOULD_MIN_PASS_RATE`, `session.exitstatus = max(..., 1)` if any suite breaches).
- Shared infrastructure lives in `tests_and_evals/evals/eval_collector.py` (singleton per worker, dict serialization for `workeroutput`).
- `EvalCaseResult` is node-neutral: `suite` (the eval node), `case_id`, `level`, `passed`, `failed_checks`, and suite-specific `details` / `metrics`. One `record(...)` carries one level, so a single input can emit one record per check at different levels (todo_extract: `who_placeholder_recall` is MUST, `what_term_coverage` / `when_term_coverage` are SHOULD).

This decision is currently in effect in production/dev workflow.

## Consequences

- Eval authors follow the usage pattern documented in `test_pii_email_eval.py` and `tests_and_evals/README.md`.
- `pytest-xdist` is an optional dev dependency (`requirements.in`).
- New eval nodes add their own `suite` and named checks (with `details`/`metrics`) without changing the session hooks.
- Node vocabulary is threaded unchanged into the eval layer (todo_extract uses `who` / `what` / `when`) to avoid cross-layer naming drift.
