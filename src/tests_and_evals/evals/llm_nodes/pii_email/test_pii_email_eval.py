"""Eval for the pii_email node against a real LLM (golden set in ``cases.json``).

What we measure (the LLM is the non-deterministic part; masking is deterministic):
- Email recall: expected emails present in ``pii_email.emails``.
- Text integrity: forbidden spans removed from ``pii_email.text``.

MUST cases gate the test (collected, asserted once at the end); SHOULD cases are
only measured/logged. Skipped automatically when smoke secrets are absent.
"""

import json
import logging
from pathlib import Path

from langchain_core.messages import HumanMessage
import pytest

from src.llm_nodes.global_state import GlobalState
from src.llm_nodes.pii_email.nodes import get_pii_email_node
from src.logging_setup import get_logger
from src.tests_and_evals.common.fixtures import get_model_for_smoke_test

logger = get_logger(__name__, "tests_and_evals/evals/llm_nodes/pii_email/test_pii_email_eval.py")
logger.setLevel(logging.INFO)


def get_cases() -> list[dict]:
    cases_file = Path(__file__).parent / "cases.json"
    with cases_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def _missing_emails(emails: list[str | None], expected_emails: list[str]) -> set[str]:
    found = {e.lower() for e in emails if e is not None}
    return {e.lower() for e in expected_emails} - found


def _leaked_spans(text: str, forbidden_spans: list[str]) -> list[str]:
    return [span for span in forbidden_spans if span in text]


@pytest.mark.eval
@pytest.mark.asyncio
async def test_pii_email_eval(get_model_for_smoke_test):
    cases = get_cases()
    model = get_model_for_smoke_test
    node = get_pii_email_node(model=model, client_cache_policy="none")
    logger.info("Running pii_email eval: %d cases", len(cases))

    summary = {
        "must_cases": 0,
        "should_cases": 0,
        "must_failures": 0,
        "email_expected_total": 0,
        "email_missing_total": 0,
        "text_forbidden_total": 0,
        "text_leaked_total": 0,
    }

    for case in cases:
        case_id = case["_metadata"]["id"]
        level = case["_metadata"]["requirement_level"]
        expected_emails = case["expected_emails"]
        forbidden_spans = case["forbidden_spans"]

        state = GlobalState(messages=[HumanMessage(content=case["input"])])
        result = await node(state)
        pii = result["pii_email"]

        missing = _missing_emails(pii.emails, expected_emails)
        leaked = _leaked_spans(pii.text, forbidden_spans)

        summary["email_expected_total"] += len(expected_emails)
        summary["email_missing_total"] += len(missing)
        summary["text_forbidden_total"] += len(forbidden_spans)
        summary["text_leaked_total"] += len(leaked)

        is_failure = bool(missing or leaked)
        log = logger.error if level == "MUST" else logger.warning
        if is_failure:
            log(
                "[case=%s] [%s] missing_emails=%s leaked_spans=%s emails=%s text=%r",
                case_id,
                level,
                sorted(missing),
                leaked,
                pii.emails,
                pii.text,
            )

        if level == "MUST":
            summary["must_cases"] += 1
            if is_failure:
                summary["must_failures"] += 1
        elif level == "SHOULD":
            summary["should_cases"] += 1

    email_recall = (
        1.0 - (summary["email_missing_total"] / summary["email_expected_total"])
        if summary["email_expected_total"]
        else 1.0
    )
    text_clean_rate = (
        1.0 - (summary["text_leaked_total"] / summary["text_forbidden_total"])
        if summary["text_forbidden_total"]
        else 1.0
    )
    logger.info(
        "pii_email eval summary | MUST=%d SHOULD=%d must_failures=%d email_recall=%.3f text_clean=%.3f",
        summary["must_cases"],
        summary["should_cases"],
        summary["must_failures"],
        email_recall,
        text_clean_rate,
    )
    assert summary["must_failures"] == 0, f"MUST eval failures: {summary['must_failures']}"
