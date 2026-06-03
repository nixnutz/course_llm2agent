# 0010 - Eval MUST/SHOULD Gating via Pytest Session Hooks

- Status: Accepted
- Date: 2026-06-03
- OverheadSeconds: 0

## Context

Golden-set evals mix hard requirements (MUST) with softer targets (SHOULD). Failing every SHOULD case inside the test function makes local LLM evals noisy; ignoring SHOULD entirely hides regressions. We also want one aggregated SHOULD pass rate per pytest run and compatibility with `pytest-xdist` without fixture-based session teardown.

## Decision

- Tests under `tests_and_evals/evals/` call `get_eval_collector()` inside each test function (never at module import), `record()` per case, and `assert` MUST failures in the test.
- `tests_and_evals/evals/conftest.py` resets the collector in `pytest_sessionstart`, merges worker results when xdist is active (`numprocesses` / `pytest_testnodedown`), and applies the SHOULD pass-rate gate in `pytest_sessionfinish` (`SHOULD_MIN_PASS_RATE`, `session.exitstatus = max(..., 1)` on breach).
- Shared infrastructure lives in `tests_and_evals/evals/eval_collector.py` (singleton per worker, dict serialization for `workeroutput`).
- `EvalCaseResult` fields (`missing_emails`, `leaked_spans`) are PII-email-shaped for now; generalize to node-neutral fields when a second eval node appears.

This decision is currently in effect in production/dev workflow.

## Consequences

- Eval authors follow the usage pattern documented in `test_pii_email_eval.py` and `tests_and_evals/README.md`.
- `pytest-xdist` is an optional dev dependency (`requirements.in`).
- Future non-PII evals should extend recording semantics without moving session hooks back into per-node paths.
