"""Eval for the todo_extract node against a real LLM (golden set in ``cases.json``).

Vocabulary is threaded unchanged from ``todo_extract/models.py``: ``who`` / ``what``
/ ``when``. We record one result per check so a single input can mix levels:

- ``who_placeholder_recall`` (MUST): the masked-email placeholders must survive into
  ``item.who`` (deterministic, exact token match).
- ``what_term_coverage`` (SHOULD): expected task terms present in some ``item.what``.
- ``when_term_coverage`` (SHOULD): expected deadline terms present in some ``item.when``.

``what`` / ``when`` use plain term matching as a course-level starting point; real
grading is LLM-as-judge later, which is why they are SHOULD, not MUST.

Eval collector usage (see ``evals/conftest.py`` hooks):
- Call ``get_eval_collector()`` inside the test function (never at module import).
- ``collector.record(...)`` per check; MUST is asserted here, SHOULD is gated per
  suite in ``pytest_sessionfinish``.

Skipped automatically when smoke secrets are absent.
"""

import json
import logging
from pathlib import Path
import re

import pytest

from src.llm_nodes.todo_extract.models import TODOState
from src.llm_nodes.todo_extract.nodes import get_todo_list_node
from src.logging_setup import get_logger
from src.tests_and_evals.evals.eval_collector import get_eval_collector

logger = get_logger(
    __name__, "tests_and_evals/evals/llm_nodes/todo_extract/test_todo_extract_eval.py"
)
logger.setLevel(logging.INFO)

_SUITE = "todo_extract"
# TODO: derive placeholder parsing from the PII module/prompt contract instead of
# duplicating the current E{n}_{salt} implementation detail in this eval.
_PLACEHOLDER_RE = re.compile(r"E\d+_[0-9a-f]+")


def get_cases() -> list[dict]:
    cases_file = Path(__file__).parent / "cases.json"
    with cases_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def _missing_terms(expected_terms: list[str], haystack: str) -> set[str]:
    """Expected terms absent from ``haystack`` (case-insensitive substring match)."""
    hay = haystack.lower()
    return {term for term in expected_terms if term.lower() not in hay}


def _placeholder_tokens(items) -> set[str]:
    """Extract exact placeholder tokens from ``item.who`` values."""
    tokens: set[str] = set()
    for item in items:
        if not item.who:
            continue
        tokens.update(_PLACEHOLDER_RE.findall(item.who))
    return tokens


@pytest.mark.eval
@pytest.mark.asyncio
async def test_todo_extract_eval(get_model_for_smoke_test):
    # Fresh singleton for this session (reset in pytest_sessionstart).
    collector = get_eval_collector()
    cases = get_cases()
    model = get_model_for_smoke_test
    node = get_todo_list_node(model=model, client_cache_policy="none")
    logger.info("Running todo_extract eval: %d cases", len(cases))

    for case in cases:
        case_id = case["_metadata"]["id"]
        expected_who_tokens = case["expected_who_tokens"]
        expected_what_terms = case.get("expected_what_terms", [])
        expected_when_terms = case.get("expected_when_terms", [])

        state = TODOState(text=case["input"])
        result = await node(state)
        items = result["todo_list"].items

        # Union across all extracted rows: a token/term counts as found if any item has it.
        all_who_tokens = _placeholder_tokens(items)
        all_what = " ".join(item.what for item in items)
        all_when = " ".join(item.when for item in items)

        missing_who_tokens = set(expected_who_tokens) - all_who_tokens
        missing_what_terms = _missing_terms(expected_what_terms, all_what)
        missing_when_terms = _missing_terms(expected_when_terms, all_when)

        if missing_who_tokens or missing_what_terms or missing_when_terms:
            logger.warning(
                "[case=%s] missing_who=%s missing_what=%s missing_when=%s items=%s input=%r",
                case_id,
                sorted(missing_who_tokens),
                sorted(missing_what_terms),
                sorted(missing_when_terms),
                [(i.who, i.what, i.when) for i in items],
                case["input"],
            )

        collector.record(
            suite=_SUITE,
            case_id=f"{case_id}:who",
            level="MUST",
            failed_checks=["who_placeholder_recall"] if missing_who_tokens else [],
            details={"missing_who_tokens": missing_who_tokens},
        )
        collector.record(
            suite=_SUITE,
            case_id=f"{case_id}:what",
            level="SHOULD",
            failed_checks=["what_term_coverage"] if missing_what_terms else [],
            details={"missing_what_terms": missing_what_terms},
        )
        if expected_when_terms:
            collector.record(
                suite=_SUITE,
                case_id=f"{case_id}:when",
                level="SHOULD",
                failed_checks=["when_term_coverage"] if missing_when_terms else [],
                details={"missing_when_terms": missing_when_terms},
            )

    suite_results = [r for r in collector.results if r.suite == _SUITE]
    must_cases = len([r for r in suite_results if r.level == "MUST"])
    should_cases = len([r for r in suite_results if r.level == "SHOULD"])
    must_failures = len([r for r in suite_results if r.level == "MUST" and not r.passed])
    logger.info(
        "todo_extract eval summary | MUST=%d SHOULD=%d must_failures=%d",
        must_cases,
        should_cases,
        must_failures,
    )
    assert must_failures == 0, f"MUST eval failures: {must_failures}"
