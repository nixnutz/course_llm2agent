"""Mocked unit tests for ``LlmNodePIIExtract`` (no real LLM).

Summary:
- Smoke: mocked LLM ``occurrences`` -> masked ``pii_email`` and ``messages``.
- Guards: no human message, non-string human content.
- Last human message is used for the prompt.
- Return shape: ``AIMessage`` with stripped LLM answer.
- OpenAI wiring: model and ``temperature=0.0``.
- Empty occurrences -> text unchanged.
- Error paths: invalid JSON, ``occurrences`` not a list.

Deterministic masking detail lives in ``test_mask.py``; here we only check the
node wiring (LLM call -> parse -> mask pipeline -> state).

Not exhaustive: course/WIP code, no real LLM.
"""

import json

from langchain_core.messages import AIMessage, HumanMessage
import pytest

from src.llm_nodes.global_state import GlobalState
from src.llm_nodes.pii_email.nodes import get_pii_email_node

_LLM_JSON = json.dumps(
    {"occurrences": [{"span": "alice@example.com", "raw": "alice@example.com"}]}
)


def _patch_openai(mocker, llm_content: str):
    mock_message = mocker.MagicMock()
    mock_message.content = llm_content
    mock_completion = mocker.MagicMock()
    mock_completion.choices = [mocker.MagicMock(message=mock_message)]
    mock_client = mocker.MagicMock()
    mock_client.chat.completions.create = mocker.AsyncMock(return_value=mock_completion)
    return mock_client, (lambda: mock_client)


@pytest.fixture
def mock_openai_for_pii(mocker):
    return _patch_openai(mocker, _LLM_JSON)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_smoke_mocked_llm_fills_state(mock_openai_for_pii):
    mock_client, client_provider = mock_openai_for_pii
    node = get_pii_email_node(model="test-model", client_provider=client_provider)
    state = GlobalState(
        messages=[HumanMessage(content="Contact alice@example.com for details.")],
    )
    result = await node(state)

    pii = result["pii_email"]
    assert "alice@example.com" not in pii.text
    assert pii.emails == ["alice@example.com"]
    assert len(pii.occurrences) == 1
    assert pii.occurrences[0].placeholder == f"E0_{pii.salt}"
    assert isinstance(result["messages"][0], AIMessage)
    assert len(result["messages"]) == 1
    assert mock_client.chat.completions.create.await_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_raises_without_human_message(mocker):
    _, client_provider = _patch_openai(mocker, _LLM_JSON)
    node = get_pii_email_node(model="test-model", client_provider=client_provider)
    with pytest.raises(ValueError, match="Expected at least one human message"):
        await node(GlobalState(messages=[]))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_raises_when_human_content_not_string(mocker):
    _, client_provider = _patch_openai(mocker, _LLM_JSON)
    node = get_pii_email_node(model="test-model", client_provider=client_provider)
    state = GlobalState(messages=[HumanMessage(content=[{"type": "text", "text": "x"}])])
    with pytest.raises(ValueError, match="Expected at least one human message"):
        await node(state)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_uses_last_human_message(mocker):
    mock_client, client_provider = _patch_openai(mocker, _LLM_JSON)
    node = get_pii_email_node(model="test-model", client_provider=client_provider)
    state = GlobalState(
        messages=[
            HumanMessage(content="First message."),
            HumanMessage(content="Second message."),
        ],
    )
    await node(state)
    call_kwargs = mock_client.chat.completions.create.await_args.kwargs
    user_payload = next(m for m in call_kwargs["messages"] if m["role"] == "user")
    assert user_payload["content"] == "Second message."


@pytest.mark.unit
@pytest.mark.asyncio
async def test_returns_ai_message_with_stripped_llm_answer(mocker):
    _, client_provider = _patch_openai(mocker, f"  {_LLM_JSON}  ")
    node = get_pii_email_node(model="test-model", client_provider=client_provider)
    state = GlobalState(messages=[HumanMessage(content="Hello.")])
    result = await node(state)
    assert isinstance(result["messages"][0], AIMessage)
    assert result["messages"][0].content == _LLM_JSON


@pytest.mark.unit
@pytest.mark.asyncio
async def test_openai_called_with_model_and_zero_temperature(mocker, mock_openai_for_pii):
    mock_client, client_provider = mock_openai_for_pii
    node = get_pii_email_node(model="test-model", client_provider=client_provider)
    state = GlobalState(messages=[HumanMessage(content="Hello.")])
    await node(state)
    call_kwargs = mock_client.chat.completions.create.await_args.kwargs
    assert call_kwargs["model"] == "test-model"
    assert call_kwargs["temperature"] == 0.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_occurrences_keeps_text_unchanged(mocker):
    empty = json.dumps({"occurrences": []})
    _, client_provider = _patch_openai(mocker, empty)
    node = get_pii_email_node(model="test-model", client_provider=client_provider)
    state = GlobalState(messages=[HumanMessage(content="No emails in reply.")])
    result = await node(state)
    assert result["pii_email"].text == "No emails in reply."
    assert result["pii_email"].emails == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_missing_occurrences_field_defaults_to_empty(mocker):
    partial = json.dumps({"unrelated": True})
    _, client_provider = _patch_openai(mocker, partial)
    node = get_pii_email_node(model="test-model", client_provider=client_provider)
    state = GlobalState(messages=[HumanMessage(content="Hello.")])
    result = await node(state)
    assert result["pii_email"].text == "Hello."
    assert result["pii_email"].emails == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_raises_on_invalid_json_from_llm(mocker):
    _, client_provider = _patch_openai(mocker, "not json")
    node = get_pii_email_node(model="test-model", client_provider=client_provider)
    state = GlobalState(messages=[HumanMessage(content="Hello.")])
    with pytest.raises(ValueError, match="Invalid JSON from model"):
        await node(state)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_raises_when_occurrences_not_a_list(mocker):
    bad = json.dumps({"occurrences": {"span": "a@b.com", "raw": "a@b.com"}})
    _, client_provider = _patch_openai(mocker, bad)
    node = get_pii_email_node(model="test-model", client_provider=client_provider)
    state = GlobalState(messages=[HumanMessage(content="Hello.")])
    with pytest.raises(ValueError, match="must be a list"):
        await node(state)
