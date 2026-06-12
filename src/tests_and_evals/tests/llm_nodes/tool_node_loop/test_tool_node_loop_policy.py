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
    route_after_llm_with_tools,
)
from src.llm_nodes.tool_node_loop.models import (
    MIN_MAX_TOOL_ERRORS,
    MIN_MAX_TOOL_ROUNDS,
    ToolNodeLoopState,
    compute_max_tool_errors,
    compute_max_tool_rounds,
)

_WHO = "E0_a1b2c3d4"
_TODO_JSON = json.dumps({"items": [{"who": _WHO, "what": "feed the cat", "when": "today"}]})

# Policy limits — source of truth: ``models.compute_max_tool_rounds`` /
# ``compute_max_tool_errors`` (derived on ``ToolNodeLoopState`` when
# ``todo_list_json`` is set).
#
# max_tool_rounds:
#   base = max(unique_non_empty_who, 1)     # greet once per distinct ``who``
#   max_tool_rounds = max(MIN_MAX_TOOL_ROUNDS, ceil(base * 1.20))
#   MIN_MAX_TOOL_ROUNDS = 3; +20% headroom when the LLM misses "unique who".
#
# max_tool_errors:
#   max_tool_errors = max(MIN_MAX_TOOL_ERRORS, floor(max_tool_rounds * 0.10))
#   MIN_MAX_TOOL_ERRORS = 3; up to 10% of the round budget may fail, then stop.
#
# Router policy stop (``route_after_llm_with_tools``): only when the last AIMessage still
# has pending tool_calls AND (tool_round >= max_tool_rounds OR
# tool_errors >= max_tool_errors). Without pending tool_calls → finalize even at
# the limit.
#
# Tests below without ``todo_list_json`` use the field defaults (minima 3 / 3).


@pytest.mark.unit
def test_compute_policy_limits_from_todo_json():
    # 1 unique who: base=1 → ceil(1*1.20)=2 → max(3,2)=3
    assert compute_max_tool_rounds(_TODO_JSON) == MIN_MAX_TOOL_ROUNDS
    # floor(3*0.10)=0 → max(3,0)=3
    assert compute_max_tool_errors(MIN_MAX_TOOL_ROUNDS) == MIN_MAX_TOOL_ERRORS

    three_who_json = json.dumps(
        {
            "items": [
                {"who": "E0_a", "what": "a", "when": "today"},
                {"who": "E1_b", "what": "b", "when": "today"},
                {"who": "E2_c", "what": "c", "when": "today"},
            ]
        }
    )
    # 3 unique who: base=3 → ceil(3*1.20)=4 → max(3,4)=4
    assert compute_max_tool_rounds(three_who_json) == 4
    # floor(4*0.10)=0 → max(3,0)=3
    assert compute_max_tool_errors(4) == MIN_MAX_TOOL_ERRORS


@pytest.mark.unit
def test_state_derives_policy_limits_from_todo_list_json():
    state = ToolNodeLoopState(todo_list_json=_TODO_JSON)
    assert state.max_tool_rounds == MIN_MAX_TOOL_ROUNDS
    assert state.max_tool_errors == MIN_MAX_TOOL_ERRORS


@pytest.mark.unit
def test_route_after_llm_with_tools_tools_vs_finalize():
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
    assert route_after_llm_with_tools(with_tool_calls) == "tools"

    final_only = ToolNodeLoopState(messages=[AIMessage(content="# Salve, E0_a1b2c3d4!")])
    assert route_after_llm_with_tools(final_only) == "finalize"


@pytest.mark.unit
def test_validate_todo_text_raises_on_missing_who():
    with pytest.raises(PipelineValidationError, match="missing placeholder who token"):
        _validate_todo_text_against_json(
            "# no placeholder tokens",
            _TODO_JSON,
            tool_errors=0,
        )


@pytest.mark.unit
def test_route_after_llm_with_tools_allows_finalize_when_policy_exhausted_but_no_tool_calls():
    # tool_round at limit, but no pending tool_calls → finalize (see policy comment above).
    state = ToolNodeLoopState(
        tool_round=MIN_MAX_TOOL_ROUNDS,
        messages=[AIMessage(content="# Salve, E0_a1b2c3d4!\n- [ ] feed the cat (by today)")],
    )
    assert route_after_llm_with_tools(state) == "finalize"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_policy_exhausted_raises_policy_violation_error():
    # tool_errors at default limit (3) with pending tool_calls → policy_exhausted.
    state = ToolNodeLoopState(
        tool_errors=MIN_MAX_TOOL_ERRORS,
        messages=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "greet", "args": {"who": _WHO}, "id": "call_1", "type": "tool_call"},
                ],
            )
        ],
    )
    assert route_after_llm_with_tools(state) == "policy_exhausted"
    with pytest.raises(PolicyViolationError, match="policy exhausted"):
        await _policy_exhausted(state)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_policy_exhausted_raises_policy_violation_error_on_max_rounds():
    # tool_round at default limit (3) with pending tool_calls → policy_exhausted.
    state = ToolNodeLoopState(
        tool_round=MIN_MAX_TOOL_ROUNDS,
        messages=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "greet", "args": {"who": _WHO}, "id": "call_2", "type": "tool_call"},
                ],
            )
        ],
    )
    assert route_after_llm_with_tools(state) == "policy_exhausted"
    with pytest.raises(PolicyViolationError, match="policy exhausted"):
        await _policy_exhausted(state)
