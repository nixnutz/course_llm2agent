"""L2 exemplar for ``ToolNodeLoopAgent`` wiring (no real LLM).

Not exhaustive: course/WIP. Scope: ADR 0011 L2 guard on empty subgraph input.
"""

import pytest

from src.errors import PipelinePreconditionError
from src.llm_nodes.tool_node_loop.models import ToolNodeLoopState
from src.llm_nodes.tool_node_loop.nodes import get_tool_node_loop_agent_node


def _mock_chat_model_provider(mocker):
    mock_llm = mocker.MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    return lambda: mock_llm


@pytest.mark.unit
@pytest.mark.asyncio
async def test_raises_on_empty_todo_list_json(mocker):
    node = get_tool_node_loop_agent_node(
        model="test-model",
        chat_model_provider=_mock_chat_model_provider(mocker),
    )
    with pytest.raises(PipelinePreconditionError, match="non-empty todo_list_json"):
        await node(ToolNodeLoopState())
