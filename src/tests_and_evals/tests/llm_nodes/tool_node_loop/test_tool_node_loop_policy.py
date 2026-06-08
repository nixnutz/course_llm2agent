"""L1 exemplars for ``tool_node_loop`` trusted policy/finalize (no LLM).

Not exhaustive: course/WIP. Scope: ADR 0011 L1 reminders for router + finalize gate.
"""

import json

from langchain_core.messages import AIMessage
import pytest

from src.errors import PipelineValidationError, PolicyViolationError
from src.llm_nodes.tool_node_loop.graph import (
    _policy_exhausted,
    _validate_todo_text_against_json,
    route_after_agent,
)
from src.llm_nodes.tool_node_loop.models import MAX_TOOL_ERRORS, MAX_TOOL_ROUNDS, ToolNodeLoopState

_WHO = "E0_a1b2c3d4"
_TODO_JSON = json.dumps({"items": [{"who": _WHO, "what": "feed the cat", "when": "today"}]})


@pytest.mark.unit
def test_route_after_agent_tools_vs_finalize():
    with_tool_calls = ToolNodeLoopState(
        messages=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "greet", "args": {"who": _WHO}, "id": "call_1", "type": "tool_call"},
                ],
            )
        ]
    )
    assert route_after_agent(with_tool_calls) == "tools"

    final_only = ToolNodeLoopState(messages=[AIMessage(content="# Salve, E0_a1b2c3d4!")])
    assert route_after_agent(final_only) == "finalize"


@pytest.mark.unit
def test_validate_todo_text_raises_on_missing_who():
    with pytest.raises(PipelineValidationError, match="missing placeholder who token"):
        _validate_todo_text_against_json(
            "# no placeholder tokens",
            _TODO_JSON,
            tool_errors=0,
        )


@pytest.mark.unit
def test_route_after_agent_allows_finalize_when_policy_exhausted_but_no_tool_calls():
    state = ToolNodeLoopState(
        tool_round=MAX_TOOL_ROUNDS,
        messages=[AIMessage(content="# Salve, E0_a1b2c3d4!\n- [ ] feed the cat (by today)")],
    )
    assert route_after_agent(state) == "finalize"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_policy_exhausted_raises_policy_violation_error():
    state = ToolNodeLoopState(
        tool_errors=MAX_TOOL_ERRORS,
        messages=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "greet", "args": {"who": _WHO}, "id": "call_1", "type": "tool_call"},
                ],
            )
        ],
    )
    assert route_after_agent(state) == "policy_exhausted"
    with pytest.raises(PolicyViolationError, match="policy exhausted"):
        await _policy_exhausted(state)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_policy_exhausted_raises_policy_violation_error_on_max_rounds():
    state = ToolNodeLoopState(
        tool_round=MAX_TOOL_ROUNDS,
        messages=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "greet", "args": {"who": _WHO}, "id": "call_2", "type": "tool_call"},
                ],
            )
        ],
    )
    assert route_after_agent(state) == "policy_exhausted"
    with pytest.raises(PolicyViolationError, match="policy exhausted"):
        await _policy_exhausted(state)
