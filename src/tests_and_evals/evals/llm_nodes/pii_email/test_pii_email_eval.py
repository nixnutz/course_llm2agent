import json
import logging
from pathlib import Path
from typing import Tuple

from langchain_core.messages import HumanMessage
import pytest

from src.llm_nodes.global_state import GlobalState
from src.llm_nodes.pii_email.nodes import get_pii_email_node
from src.tests_and_evals.common.fixtures import get_model_for_smoke_test
from src.logging_setup import get_logger

logger = get_logger(__name__, "tests_and_evals/evals/llm_nodes/pii_email/test_pii_email_eval.py")
logger.setLevel(logging.INFO)


def get_cases() -> list[dict]:
    cases_file = Path(__file__).parent / "cases.json"
    with cases_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def _fmt_emails(values: list[str]) -> str:
    if not values:
        return "[]"
    return "[" + ", ".join(values) + "]"


def validate_recognized_emails(
    recognized_emails: list[str],
    expected_recognized_emails: list[str],
    requirement_level: str,
    case_id: str,
) -> Tuple[bool, int, int]:
    return validate_emails(
        "recognized",
        recognized_emails,
        expected_recognized_emails,
        requirement_level,
        case_id,
    )


def validate_raw_emails(
    raw_emails: list[str], expected_raw_emails: list[str], requirement_level: str, case_id: str
) -> Tuple[bool, int, int]:
    return validate_emails("raw", raw_emails, expected_raw_emails, requirement_level, case_id)


def validate_emails(
    which_emails: str,
    actual_emails: list[str],
    expected_emails: list[str],
    requirement_level: str,
    case_id: str,
) -> Tuple[bool, int, int]:
    expected_set = set(expected_emails)
    actual_set = set(actual_emails)
    missing = expected_set - actual_set
    extra = actual_set - expected_set
    summary = f"[case={case_id}] [{requirement_level}] [{which_emails}]"
    if requirement_level == "MUST":
        if missing:
            logger.error(
                "%s missing=%s extra=%s expected=%s got=%s",
                summary,
                sorted(missing),
                sorted(extra),
                _fmt_emails(expected_emails),
                _fmt_emails(actual_emails),
            )
            return False, len(missing), len(expected_set)
        return True, 0, len(expected_set)

    if requirement_level == "SHOULD":
        if missing:
            logger.warning(
                "%s missing=%s extra=%s expected=%s got=%s",
                summary,
                sorted(missing),
                sorted(extra),
                _fmt_emails(expected_emails),
                _fmt_emails(actual_emails),
            )
            return True, len(missing), len(expected_set)
        return True, 0, len(expected_set)

    return True, 0, len(expected_set)


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
        "raw_expected_total": 0,
        "raw_missing_total": 0,
        "recognized_expected_total": 0,
        "recognized_missing_total": 0,
    }

    for case in cases:
        case_id = case["_metadata"]["id"]
        requirement_level = case["_metadata"]["requirement_level"]
        input_text = case["input"]
        expected_recognized_emails = case["expected_recognized_emails"]
        expected_raw_emails = case["expected_raw_emails"]

        state = GlobalState(messages=[HumanMessage(content=input_text)])
        result = await node(state)
        if requirement_level == "MUST":
            summary["must_cases"] += 1
        elif requirement_level == "SHOULD":
            summary["should_cases"] += 1

        success, num_missing, expected_count = validate_raw_emails(
            result["pii_email"].raw_emails,
            expected_raw_emails,
            requirement_level,
            case_id,
        )
        summary["raw_expected_total"] += expected_count
        summary["raw_missing_total"] += num_missing
        if not success:
            summary["must_failures"] += 1

        success, num_missing, expected_count = validate_recognized_emails(
            result["pii_email"].recognized_emails,
            expected_recognized_emails,
            requirement_level,
            case_id,
        )
        summary["recognized_expected_total"] += expected_count
        summary["recognized_missing_total"] += num_missing
        if not success:
            summary["must_failures"] += 1

    raw_recall = (
        1.0 - (summary["raw_missing_total"] / summary["raw_expected_total"])
        if summary["raw_expected_total"]
        else 1.0
    )
    recognized_recall = (
        1.0 - (summary["recognized_missing_total"] / summary["recognized_expected_total"])
        if summary["recognized_expected_total"]
        else 1.0
    )
    logger.info(
        "pii_email eval summary | MUST=%d SHOULD=%d must_failures=%d raw_recall=%.3f recognized_recall=%.3f",
        summary["must_cases"],
        summary["should_cases"],
        summary["must_failures"],
        raw_recall,
        recognized_recall,
    )
    assert summary["must_failures"] == 0, f"MUST eval failures: {summary['must_failures']}"
