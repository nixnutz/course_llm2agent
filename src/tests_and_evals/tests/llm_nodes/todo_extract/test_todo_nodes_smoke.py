"""Smoke integration tests for the TODO extraction node (real LLM call).

Not exhaustive: course/WIP code. Evals cover stricter golden-set behavior.
"""

import re

import pytest

from src.llm_nodes.todo_extract.models import TODOState
from src.llm_nodes.todo_extract.nodes import get_todo_list_node

_PLACEHOLDER_RE = re.compile(r"^E\d+_[0-9a-f]+$")


@pytest.mark.smoke
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("text", "expected_placeholder"),
    [
        ("Task E0_a1b2c3d4 to feed the cat today.", "E0_a1b2c3d4"),
    ],
)
async def test_todo_extract_node_smoke_real_llm_extracts_placeholder_todo(
    get_model_for_smoke_test, text, expected_placeholder
):
    model = get_model_for_smoke_test

    node = get_todo_list_node(model=model, client_cache_policy="none")
    state = TODOState(text=text)

    result = await node(state)

    assert "todo_list" in result
    assert "messages" in result
    assert result["messages"], "expected at least one trace message"

    todo_list = result["todo_list"]
    assert todo_list.items, "expected at least one extracted TODO item"
    assert any(item.what.strip() for item in todo_list.items), "expected a non-empty task text"

    who_values = [item.who for item in todo_list.items if item.who]
    assert who_values, "expected at least one non-empty who field"
    assert any(expected_placeholder in who or _PLACEHOLDER_RE.match(who) for who in who_values), (
        f"expected placeholder-like who; got who_values={who_values}"
    )
