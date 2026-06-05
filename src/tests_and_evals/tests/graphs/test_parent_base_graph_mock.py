"""Mock E2E for ``build_parent_base_graph`` (L3 pipeline reminder; all LLMs mocked).

Not exhaustive: course/WIP. Per-node wiring: L2 mocks; demask restore logic: ``test_mask.py``.
"""

import json
import re

from langchain_core.messages import HumanMessage
import pytest

from src.graphs.parent_base_graph import build_parent_base_graph
from src.llm_nodes.global_state import GlobalState
from src.reducer.base_reader import BaseReducerReader
from src.reducer.reducer_session import reducer_session

_PLACEHOLDER_RE = re.compile(r"E\d+_[0-9a-f]+")
_PII_JSON = json.dumps(
    {"occurrences": [{"span": "alice@example.com", "raw": "alice@example.com"}]}
)

def _patch_openai_for_parent_graph(mocker):
    call_state = {"n": 0}

    async def llm_create(**kwargs):
        messages = kwargs["messages"]
        user_content = next(m["content"] for m in messages if m["role"] == "user")
        n = call_state["n"]
        call_state["n"] += 1

        mock_message = mocker.MagicMock()
        if n == 0:
            mock_message.content = _PII_JSON
        elif n == 1:
            placeholders = _PLACEHOLDER_RE.findall(user_content)
            assert placeholders, f"expected placeholder in todo_extract prompt: {user_content!r}"
            ph = placeholders[0]
            mock_message.content = json.dumps(
                {"items": [{"who": ph, "what": "call alice", "when": "today"}]}
            )
        else:
            placeholders = _PLACEHOLDER_RE.findall(user_content)
            assert placeholders, f"expected placeholder in todo_markdown prompt: {user_content!r}"
            ph = placeholders[0]
            mock_message.content = f"# {ph}\n- [ ] call alice (by today)"

        mock_completion = mocker.MagicMock()
        mock_completion.choices = [mocker.MagicMock(message=mock_message)]
        return mock_completion

    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create = mocker.AsyncMock(side_effect=llm_create)

    def provider():
        return mock_client

    mocker.patch("src.graphs.parent_base_graph.make_async_openai_client_provider", return_value=provider)
    return mock_client


def make_reader(get_thread_id):
    return BaseReducerReader(get_thread_id=get_thread_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_parent_graph_mock_e2e_restores_email_in_todo_markdown(mocker):
    mock_client = _patch_openai_for_parent_graph(mocker)
    bundle = build_parent_base_graph("test-model")

    with reducer_session("test-thread", factory=make_reader) as session:
        state = GlobalState(
            messages=[HumanMessage(content="Contact alice@example.com for details.")],
        )
        result = await session.ainvoke(bundle.graph, state)

    markdown = result["todo_markdown"].markdown
    assert "alice@example.com" in markdown
    assert not _PLACEHOLDER_RE.search(markdown)
    assert mock_client.chat.completions.create.await_count == 3
