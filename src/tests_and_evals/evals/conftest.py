"""Eval pytest hooks: reset collector at session start, SHOULD gate at session end.

Single-process runs merge from ``get_eval_collector()``; xdist workers export via
``workeroutput`` and the controller merges chunks in ``pytest_testnodedown``.
"""

from pytest import StashKey

from src.logging_setup import get_logger
from src.tests_and_evals.evals.eval_collector import (
    EvalCaseResult,
    get_eval_collector,
    reset_eval_collector,
    results_from_dicts,
    results_to_dicts,
)

logger = get_logger(__name__, __file__)

eval_worker_chunks_key = StashKey[list[list[dict]]]()

SHOULD_MIN_PASS_RATE = 0.8


def _should_summary(results: list[EvalCaseResult]) -> tuple[int, int, list[EvalCaseResult]]:
    should = [r for r in results if r.level == "SHOULD"]
    failed = [r for r in should if not r.passed]
    passed = len(should) - len(failed)
    return len(should), passed, failed


def _suites(results: list[EvalCaseResult]) -> list[str]:
    """Distinct suite names, in first-seen order, so each suite is gated on its own."""
    seen: list[str] = []
    for r in results:
        if r.suite not in seen:
            seen.append(r.suite)
    return seen


def _finalize_should(session, results: list[EvalCaseResult]) -> None:
    """Summarize and gate the SHOULD pass rate per suite (one gate per eval node)."""
    breached = False
    for suite in _suites(results):
        suite_results = [r for r in results if r.suite == suite]
        total, passed, failed = _should_summary(suite_results)
        if total == 0:
            continue

        rate = passed / total
        suite_breached = rate < SHOULD_MIN_PASS_RATE
        summary_msg = "SHOULD summary suite=%s: %d/%d passed (%.0f%%, min %.0f%%)"
        summary_args = (suite, passed, total, rate * 100, SHOULD_MIN_PASS_RATE * 100)
        if suite_breached:
            logger.error(summary_msg, *summary_args)
        else:
            logger.info(summary_msg, *summary_args)

        case_log = logger.error if suite_breached else logger.warning
        for r in failed:
            case_log(
                "SHOULD fail suite=%s case=%s failed_checks=%s details=%s",
                r.suite,
                r.case_id,
                r.failed_checks,
                r.details,
            )
        breached = breached or suite_breached

    if breached:
        session.exitstatus = max(session.exitstatus, 1)


def _xdist_active(config) -> bool:
    if not config.pluginmanager.hasplugin("xdist"):
        return False
    # ``-n`` sets ``numprocesses``; ``dist`` alone is a scheduler mode and may stay ``no``.
    num = config.getoption("numprocesses", default=None)
    if num not in (None, 0, "0"):
        return True
    return config.getoption("dist", default="no") != "no"


def pytest_configure(config):
    if hasattr(config, "workerinput"):
        return
    config.stash[eval_worker_chunks_key] = []


def pytest_testnodedown(node, error):
    if eval_worker_chunks_key not in node.config.stash:
        return
    chunk = node.workeroutput.get("eval_results", [])
    node.config.stash[eval_worker_chunks_key].append(chunk)


def pytest_sessionstart(session):
    reset_eval_collector()


def pytest_sessionfinish(session, exitstatus):
    config = session.config

    if hasattr(config, "workerinput"):
        config.workeroutput["eval_results"] = results_to_dicts(get_eval_collector().results)
        return

    if _xdist_active(config):
        merged: list[EvalCaseResult] = []
        for chunk in config.stash.get(eval_worker_chunks_key, []):
            merged.extend(results_from_dicts(chunk))
    else:
        merged = get_eval_collector().results

    _finalize_should(session, merged)
