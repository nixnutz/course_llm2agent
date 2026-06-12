"""L3 exemplar: scripted tool_node_sysbox_bash subgraph (fake LLM, mock SandboxClient).

Not exhaustive: course/WIP. Scope: ADR 0011 L3 mock E2E for llm_with_tools ↔ run_tools ↔ finalize.
"""

import json
from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
import pytest

from src.llm_nodes.tool_node_sysbox_bash.client import ExecResponse, SessionCreateResponse
from src.llm_nodes.tool_node_sysbox_bash.graph import (
    _audit_placeholders,
    _bump_tool_policy,
    _finalize,
    _policy_exhausted,
    route_after_bump,
    route_after_llm_with_bash,
)
from src.llm_nodes.tool_node_sysbox_bash.models import ToolNodeSysboxBashState
from src.llm_nodes.tool_node_sysbox_bash.nodes import get_run_fence_retry_node, get_run_tools_node
from src.reducer.base_reader import BaseReducerReader
from src.reducer.reducer_session import reducer_session

_WHO = "E0_a1b2c3d4"
_SESSION_ID = "test-session-abc"
_TODO_JSON = json.dumps({"items": [{"who": _WHO, "what": "plant a tree", "when": "today"}]})
_FINAL_MD = f"# {_WHO}\n- [ ] tree a plant (3 words) (by today)"


def _mock_client() -> AsyncMock:
    client = AsyncMock()
    client.start_session.return_value = SessionCreateResponse(
        session_id=_SESSION_ID,
        container_name="sbash-test",
        container_id="cid",
    )
    client.execute_in_session.return_value = ExecResponse(
        session_id=_SESSION_ID,
        run_id="1",
        stdout="3\ntree a plant\n",
        stderr="",
        exit_code=0,
        timed_out=False,
        output_limit_exceeded=False,
        elapsed_ms=12,
        metadata_path="/tmp/meta.json",
        metadata={},
    )
    client.end_session.return_value = None
    return client


def _build_scripted_subgraph(
    llm_with_bash_node,
    sandbox_client,
    *,
    llm_fence_retry_node=None,
):
    builder = StateGraph(ToolNodeSysboxBashState)
    builder.add_node("llm_with_bash", llm_with_bash_node)
    fence_llm = llm_fence_retry_node or llm_with_bash_node
    builder.add_node("llm_fence_retry", fence_llm)
    builder.add_node("run_tools", get_run_tools_node(sandbox_client))
    builder.add_node("run_fence_retry", get_run_fence_retry_node(sandbox_client))
    builder.add_node("bump_tool_policy", _bump_tool_policy)
    builder.add_node("policy_exhausted", _policy_exhausted)
    builder.add_node("finalize", _finalize)
    builder.add_node("audit_placeholders", _audit_placeholders)

    builder.add_edge(START, "llm_with_bash")
    builder.add_conditional_edges(
        "llm_with_bash",
        route_after_llm_with_bash,
        {
            "run_tools": "run_tools",
            "policy_exhausted": "policy_exhausted",
            "finalize": "finalize",
        },
    )
    builder.add_edge("run_tools", "bump_tool_policy")
    builder.add_conditional_edges(
        "bump_tool_policy",
        route_after_bump,
        {
            "llm_fence_retry": "llm_fence_retry",
            "llm_with_bash": "llm_with_bash",
            "policy_exhausted": "policy_exhausted",
        },
    )
    builder.add_edge("llm_fence_retry", "run_fence_retry")
    builder.add_edge("run_fence_retry", "bump_tool_policy")
    builder.add_edge("finalize", "audit_placeholders")
    builder.add_edge("audit_placeholders", END)
    builder.add_edge("policy_exhausted", END)
    return builder.compile()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scripted_sysbox_loop_produces_result_text():
    llm_calls = {"n": 0}
    mock_client = _mock_client()

    async def fake_llm_with_bash(_state: ToolNodeSysboxBashState) -> dict:
        llm_calls["n"] += 1
        if llm_calls["n"] == 1:
            return {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "bash",
                                "args": {"script": "echo 'plant a tree' | wc -w"},
                                "id": "call_1",
                                "type": "tool_call",
                            }
                        ],
                    )
                ]
            }
        return {"messages": [AIMessage(content=_FINAL_MD)]}

    graph = _build_scripted_subgraph(fake_llm_with_bash, mock_client)

    def make_reader(get_thread_id):
        return BaseReducerReader(get_thread_id=get_thread_id)

    with reducer_session("test-tool-node-sysbox-bash", factory=make_reader) as session:
        result = await session.ainvoke(
            graph,
            {
                "todo_list_json": _TODO_JSON,
                "sandbox_session_id": _SESSION_ID,
                "graph_invoke_id": "invoke-1",
            },
        )

    assert result["result_text"] == _FINAL_MD
    assert llm_calls["n"] == 2
    mock_client.execute_in_session.assert_awaited_once()
    assert _WHO in result["result_text"]


_SESSION7_STDERR = (
    'script.sh: line 21: unexpected EOF while looking for matching `"\''
)
_FENCE_SCRIPT = "echo 'plant a tree' | wc -w"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scripted_sysbox_transport_retry_then_finalize():
    llm_calls = {"n": 0}
    fence_calls = {"n": 0}
    mock_client = _mock_client()
    exec_results = [
        ExecResponse(
            session_id=_SESSION_ID,
            run_id="1",
            stdout="",
            stderr=_SESSION7_STDERR,
            exit_code=2,
            timed_out=False,
            output_limit_exceeded=False,
            elapsed_ms=12,
            metadata_path="/tmp/meta.json",
            metadata={},
        ),
        ExecResponse(
            session_id=_SESSION_ID,
            run_id="2",
            stdout="3\ntree a plant\n",
            stderr="",
            exit_code=0,
            timed_out=False,
            output_limit_exceeded=False,
            elapsed_ms=12,
            metadata_path="/tmp/meta.json",
            metadata={},
        ),
    ]
    mock_client.execute_in_session.side_effect = exec_results

    async def fake_llm_with_bash(_state: ToolNodeSysboxBashState) -> dict:
        llm_calls["n"] += 1
        if llm_calls["n"] == 1:
            return {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "bash",
                                "args": {"script": "broken awk quotes"},
                                "id": "call_1",
                                "type": "tool_call",
                            }
                        ],
                    )
                ]
            }
        return {"messages": [AIMessage(content=_FINAL_MD)]}

    async def fake_llm_fence_retry(_state: ToolNodeSysboxBashState) -> dict:
        fence_calls["n"] += 1
        return {"messages": [AIMessage(content=f"```bash\n{_FENCE_SCRIPT}\n```")]}

    graph = _build_scripted_subgraph(
        fake_llm_with_bash,
        mock_client,
        llm_fence_retry_node=fake_llm_fence_retry,
    )

    def make_reader(get_thread_id):
        return BaseReducerReader(get_thread_id=get_thread_id)

    with reducer_session("test-tool-node-sysbox-bash-retry", factory=make_reader) as session:
        result = await session.ainvoke(
            graph,
            {
                "todo_list_json": _TODO_JSON,
                "sandbox_session_id": _SESSION_ID,
                "graph_invoke_id": "invoke-retry",
            },
        )

    assert result["result_text"] == _FINAL_MD
    assert llm_calls["n"] == 2
    assert fence_calls["n"] == 1
    assert mock_client.execute_in_session.await_count == 2
    assert result.get("tool_errors", 0) == 0
