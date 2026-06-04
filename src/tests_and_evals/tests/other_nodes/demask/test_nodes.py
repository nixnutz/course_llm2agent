"""Minimal unit tests for ``demask_todo_markdown_node`` (trusted restore, no LLM).

``demask_pii_emails`` behavior is covered in ``test_mask.py``; here we only
check node guards and state wiring (``todo_markdown`` + ``AIMessage`` trace).

Not exhaustive: course/WIP code.
"""

from langchain_core.messages import AIMessage
import pytest

from src.llm_nodes.global_state import GlobalState
from src.llm_nodes.pii_email.mask import mask_pii_emails
from src.llm_nodes.todo_markdown.models import TODOMarkdown
from src.other_nodes.demask.nodes import demask_todo_markdown_node, get_demask_node


@pytest.mark.unit
@pytest.mark.asyncio
async def test_raises_on_empty_todo_markdown():
    state = GlobalState(todo_markdown=TODOMarkdown(markdown=""))
    with pytest.raises(ValueError, match="non-empty todo_markdown"):
        await demask_todo_markdown_node(state)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_restore_updates_todo_markdown_and_messages():
    inp = "Contact alice@example.com for details."
    pii = mask_pii_emails(inp, [{"span": "alice@example.com", "raw": "alice@example.com"}])
    masked_md = f"TODO: call {pii.occurrences[0].placeholder}"
    state = GlobalState(todo_markdown=TODOMarkdown(markdown=masked_md), pii_email=pii)

    result = await demask_todo_markdown_node(state)

    assert "alice@example.com" in result["todo_markdown"].markdown
    assert pii.occurrences[0].placeholder not in result["todo_markdown"].markdown
    assert isinstance(result["messages"][0], AIMessage)
    assert result["messages"][0].content == result["todo_markdown"].markdown


@pytest.mark.unit
def test_get_demask_node_returns_node_callable():
    assert get_demask_node() is demask_todo_markdown_node
