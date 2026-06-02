"""Smoke integration tests for pii email node (real LLM call)."""

from langchain_core.messages import HumanMessage
import pytest

from src.llm_nodes.global_state import GlobalState
from src.llm_nodes.pii_email.nodes import get_pii_email_node
from src.tests_and_evals.common.fixtures import get_model_for_smoke_test


@pytest.mark.smoke
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("text", "expected_emails"),
    [
        ("Contact alice@example.com for details.", ["alice@example.com"]),
        (
            "Contact bob@example.com and charlie@example.com for details.",
            ["bob@example.com", "charlie@example.com"],
        ),
        ("Contact alice at example dot com for details.", ["alice@example.com"]),
    ],
)
async def test_pii_email_node_smoke_real_llm_extracts_at_least_one_email(
    get_model_for_smoke_test, text, expected_emails
):
    model = get_model_for_smoke_test

    node = get_pii_email_node(model=model, client_cache_policy="none")
    state = GlobalState(messages=[HumanMessage(content=text)])

    result = await node(state)

    assert "pii_email" in result
    assert "messages" in result
    assert result["messages"], "expected at least one trace message"
    assert result["pii_email"].raw_emails, "expected at least one extracted raw email"
    assert result["pii_email"].recognized_emails, "expected at least one recognized email"

    raw_emails = {e.lower() for e in result["pii_email"].raw_emails}
    missing = {e.lower() for e in expected_emails} - raw_emails
    assert not missing, f"missing expected emails: {missing}; got raw={raw_emails}"
