"""L2 exemplar for ``ToolNodeLoopAgent`` wiring (no real LLM).

Not exhaustive: course/WIP. Scope: ADR 0011 L2 guard on empty subgraph input.
"""

import pytest

from src.llm_nodes.tool_node_loop.models import ToolNodeLoopState
from src.llm_nodes.tool_node_loop.nodes import get_tool_node_loop_agent_node


def _mock_client_provider(mocker):
    mock_client = mocker.MagicMock()
    mock_client.base_url = "http://test"
    mock_client.api_key = "test-key"
    return lambda: mock_client


@pytest.mark.unit
@pytest.mark.asyncio
async def test_raises_on_empty_todo_list_json(mocker):
    node = get_tool_node_loop_agent_node(
        model="test-model",
        client_provider=_mock_client_provider(mocker),
    )
    with pytest.raises(ValueError, match="non-empty todo_list_json"):
        await node(ToolNodeLoopState())
