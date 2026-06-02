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

    pii = result["pii_email"]
    assert pii.occurrences, "expected at least one detected occurrence"
    assert pii.identities, "expected at least one normalized identity"

    identities = {e.lower() for e in pii.identities if e is not None}
    missing = {e.lower() for e in expected_emails} - identities
    assert not missing, f"missing expected emails: {missing}; got identities={identities}"

    # Masking must remove the original email forms from the redacted text.
    for email in expected_emails:
        assert email not in pii.text, f"email {email!r} leaked into masked text"
