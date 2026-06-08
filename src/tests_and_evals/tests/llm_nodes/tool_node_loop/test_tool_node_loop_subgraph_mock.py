"""L3 exemplar: scripted ``tool_node_loop`` subgraph (fake agent, real ToolNode).

Not exhaustive: course/WIP. Scope: ADR 0011 L3 mock E2E for agent ↔ tools ↔ finalize.
"""

import json

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
import pytest

from src.llm_nodes.tool_node_loop.graph import (
    _audit_placeholders,
    _bump_tool_policy,
    _finalize,
    _policy_exhausted,
    route_after_agent,
)
from src.llm_nodes.tool_node_loop.models import ToolNodeLoopState
from src.llm_nodes.tool_node_loop.nodes import get_tool_node_loop_tool_node
from src.reducer.base_reader import BaseReducerReader
from src.reducer.reducer_session import reducer_session

_WHO = "E0_a1b2c3d4"
_TODO_JSON = json.dumps({"items": [{"who": _WHO, "what": "feed the cat", "when": "today"}]})
_FINAL_MD = f"# Salve, {_WHO}!\n- [ ] feed the cat (by today)"


def _build_scripted_subgraph(agent_node):
    builder = StateGraph(ToolNodeLoopState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", get_tool_node_loop_tool_node())
    builder.add_node("bump_tool_policy", _bump_tool_policy)
    builder.add_node("policy_exhausted", _policy_exhausted)
    builder.add_node("finalize", _finalize)
    builder.add_node("audit_placeholders", _audit_placeholders)

    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        route_after_agent,
        {"tools": "tools", "policy_exhausted": "policy_exhausted", "finalize": "finalize"},
    )
    builder.add_edge("tools", "bump_tool_policy")
    builder.add_edge("bump_tool_policy", "agent")
    builder.add_edge("finalize", "audit_placeholders")
    builder.add_edge("audit_placeholders", END)
    return builder.compile()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scripted_tool_loop_produces_todo_text():
    agent_calls = {"n": 0}

    async def fake_agent(_state: ToolNodeLoopState) -> dict:
        agent_calls["n"] += 1
        if agent_calls["n"] == 1:
            return {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "greet",
                                "args": {"who": _WHO},
                                "id": "call_1",
                                "type": "tool_call",
                            }
                        ],
                    )
                ]
            }
        return {"messages": [AIMessage(content=_FINAL_MD)]}

    graph = _build_scripted_subgraph(fake_agent)

    def make_reader(get_thread_id):
        return BaseReducerReader(get_thread_id=get_thread_id)

    with reducer_session("test-tool-node-loop", factory=make_reader) as session:
        result = await session.ainvoke(graph, {"todo_list_json": _TODO_JSON})

    assert result["todo_text"] == _FINAL_MD
    assert agent_calls["n"] == 2
    assert any(isinstance(m, AIMessage) for m in result["messages"])
