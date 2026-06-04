"""Mocked unit tests for ``LlmNodeTODOList`` (no real LLM).

Summary:
- Smoke: mocked LLM ``items`` -> ``todo_list`` and trace ``messages``.
- Guard: empty subgraph input text.
- Redacted ``TODOState.text`` is used for the prompt.
- Return shape: ``AIMessage`` with stripped LLM answer.
- OpenAI wiring: model and ``temperature=0.0``.
- Empty items are accepted.
- Error paths: invalid JSON and schema mismatch.

JSON fence/format details live in ``test_parse_llm_json.py``; here we only check
node wiring (LLM call -> parse -> state).

Not exhaustive: course/WIP code, no real LLM.
"""

import json

from langchain_core.messages import AIMessage
import pytest

from src.llm_nodes.todo_extract.models import TODOState
from src.llm_nodes.todo_extract.nodes import get_todo_list_node

_INPUT_TEXT = "Task E0_a1b2c3d4 to feed the cat today."
_LLM_JSON = json.dumps({"items": [{"who": "E0_a1b2c3d4", "what": "feed the cat", "when": "today"}]})


def _patch_openai(mocker, llm_content: str):
    mock_message = mocker.MagicMock()
    mock_message.content = llm_content
    mock_completion = mocker.MagicMock()
    mock_completion.choices = [mocker.MagicMock(message=mock_message)]
    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create = mocker.AsyncMock(return_value=mock_completion)
    return mock_client, (lambda: mock_client)


@pytest.fixture
def mock_openai_for_todo(mocker):
    return _patch_openai(mocker, _LLM_JSON)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_smoke_mocked_llm_fills_state(mock_openai_for_todo):
    mock_client, client_provider = mock_openai_for_todo
    node = get_todo_list_node(model="test-model", client_provider=client_provider)
    state = TODOState(text=_INPUT_TEXT)

    result = await node(state)

    todo_list = result["todo_list"]
    assert len(todo_list.items) == 1
    assert todo_list.items[0].who == "E0_a1b2c3d4"
    assert todo_list.items[0].what == "feed the cat"
    assert todo_list.items[0].when == "today"
    assert isinstance(result["messages"][0], AIMessage)
    assert len(result["messages"]) == 1
    assert mock_client.chat.completions.create.await_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_raises_on_empty_text(mocker):
    _, client_provider = _patch_openai(mocker, _LLM_JSON)
    node = get_todo_list_node(model="test-model", client_provider=client_provider)
    with pytest.raises(ValueError, match="Expected non-empty text"):
        await node(TODOState())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_uses_state_text_for_prompt(mock_openai_for_todo):
    mock_client, client_provider = mock_openai_for_todo
    node = get_todo_list_node(model="test-model", client_provider=client_provider)

    await node(TODOState(text=_INPUT_TEXT))

    call_kwargs = mock_client.chat.completions.create.await_args.kwargs
    user_payload = next(m for m in call_kwargs["messages"] if m["role"] == "user")
    assert user_payload["content"] == _INPUT_TEXT


@pytest.mark.unit
@pytest.mark.asyncio
async def test_returns_ai_message_with_stripped_llm_answer(mocker):
    _, client_provider = _patch_openai(mocker, f"  {_LLM_JSON}  ")
    node = get_todo_list_node(model="test-model", client_provider=client_provider)

    result = await node(TODOState(text=_INPUT_TEXT))

    assert isinstance(result["messages"][0], AIMessage)
    assert result["messages"][0].content == _LLM_JSON


@pytest.mark.unit
@pytest.mark.asyncio
async def test_openai_called_with_model_and_zero_temperature(mock_openai_for_todo):
    mock_client, client_provider = mock_openai_for_todo
    node = get_todo_list_node(model="test-model", client_provider=client_provider)

    await node(TODOState(text=_INPUT_TEXT))

    call_kwargs = mock_client.chat.completions.create.await_args.kwargs
    assert call_kwargs["model"] == "test-model"
    assert call_kwargs["temperature"] == 0.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_items_are_accepted(mocker):
    empty = json.dumps({"items": []})
    _, client_provider = _patch_openai(mocker, empty)
    node = get_todo_list_node(model="test-model", client_provider=client_provider)

    result = await node(TODOState(text="No TODO items here."))

    assert result["todo_list"].items == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_raises_on_invalid_json_from_llm(mocker):
    _, client_provider = _patch_openai(mocker, "not json")
    node = get_todo_list_node(model="test-model", client_provider=client_provider)
    with pytest.raises(ValueError, match="Invalid JSON from model"):
        await node(TODOState(text=_INPUT_TEXT))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_raises_when_items_is_not_a_list(mocker):
    bad = json.dumps({"items": "not-a-list"})
    _, client_provider = _patch_openai(mocker, bad)
    node = get_todo_list_node(model="test-model", client_provider=client_provider)
    with pytest.raises(ValueError, match="JSON does not match schema"):
        await node(TODOState(text=_INPUT_TEXT))
