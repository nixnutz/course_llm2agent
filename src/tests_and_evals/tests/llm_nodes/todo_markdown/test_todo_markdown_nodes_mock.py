"""Mocked unit tests for ``LlmNodeTODOMarkdown`` (no real LLM).

Summary:
- Smoke: mocked LLM markdown -> ``todo_markdown`` and trace ``messages``.
- Guard: empty ``todo_list_json``.

Not exhaustive: course/WIP code, no real LLM.
"""

import json

from langchain_core.messages import AIMessage
import pytest

from src.llm_nodes.todo_markdown.models import TODOMarkdownState
from src.llm_nodes.todo_markdown.nodes import get_todo_markdown_node

_TODO_JSON = json.dumps(
    {"items": [{"who": "E0_a1b2c3d4", "what": "feed the cat", "when": "today"}]}
)
_LLM_MD = "# E0_a1b2c3d4\n- [ ] feed the cat (by today)"


def _patch_openai(mocker, llm_content: str):
    mock_message = mocker.MagicMock()
    mock_message.content = llm_content
    mock_completion = mocker.MagicMock()
    mock_completion.choices = [mocker.MagicMock(message=mock_message)]
    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create = mocker.AsyncMock(return_value=mock_completion)
    return mock_client, (lambda: mock_client)


@pytest.fixture
def mock_openai_for_todo_markdown(mocker):
    return _patch_openai(mocker, _LLM_MD)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_smoke_mocked_llm_fills_state(mock_openai_for_todo_markdown):
    mock_client, client_provider = mock_openai_for_todo_markdown
    node = get_todo_markdown_node(model="test-model", client_provider=client_provider)
    state = TODOMarkdownState(todo_list_json=_TODO_JSON)

    result = await node(state)

    assert result["todo_markdown"].markdown == _LLM_MD
    assert isinstance(result["messages"][0], AIMessage)
    assert result["messages"][0].content == _LLM_MD
    assert mock_client.chat.completions.create.await_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_raises_on_empty_todo_list_json(mocker):
    _, client_provider = _patch_openai(mocker, _LLM_MD)
    node = get_todo_markdown_node(model="test-model", client_provider=client_provider)
    with pytest.raises(ValueError, match="non-empty todo_list_json"):
        await node(TODOMarkdownState())
