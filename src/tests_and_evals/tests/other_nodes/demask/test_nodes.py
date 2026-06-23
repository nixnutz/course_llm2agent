"""Minimal unit tests for ``demask_final_result_node`` (trusted restore, no LLM).

``demask_pii_emails`` behavior is covered in ``test_mask.py``; here we only
check node guards and state wiring (``final_result`` + ``AIMessage`` trace).

Not exhaustive: course/WIP code.
"""

from langchain_core.messages import AIMessage
import pytest

from src.errors import PipelinePreconditionError
from src.llm_nodes.global_state import GlobalState
from src.llm_nodes.pii_email.mask import mask_pii_emails
from src.other_nodes.demask.nodes import demask_final_result_node, get_demask_node


@pytest.mark.unit
@pytest.mark.asyncio
async def test_raises_on_empty_final_result():
    state = GlobalState(final_result="")
    with pytest.raises(PipelinePreconditionError, match="non-empty final_result"):
        await demask_final_result_node(state)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_restore_updates_final_result_and_messages():
    inp = "Contact alice@example.com for details."
    pii = mask_pii_emails(inp, [{"span": "alice@example.com", "raw": "alice@example.com"}])
    masked_md = f"TODO: call {pii.occurrences[0].placeholder}"
    state = GlobalState(final_result=masked_md, pii_email=pii)

    result = await demask_final_result_node(state)

    assert "alice@example.com" in result["final_result"]
    assert pii.occurrences[0].placeholder not in result["final_result"]
    assert isinstance(result["messages"][0], AIMessage)
    assert result["messages"][0].content == result["final_result"]


@pytest.mark.unit
def test_get_demask_node_returns_node_callable():
    assert get_demask_node() is demask_final_result_node
