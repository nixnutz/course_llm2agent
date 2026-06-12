"""L1 exemplars for tool_node_sysbox_bash policy/finalize (no LLM).

Not exhaustive: course/WIP. Scope: ADR 0011 L1 exemplar for router + who-only finalize.
"""

import json

from langchain_core.messages import AIMessage
import pytest

from src.errors import PipelineValidationError, PolicyViolationError
from src.llm_nodes.tool_node_sysbox_bash.graph import (
    _policy_exhausted,
    _validate_result_text_against_json,
    route_after_bump,
    route_after_llm_with_bash,
)
from src.llm_nodes.tool_node_sysbox_bash.models import (
    MIN_MAX_TOOL_ERRORS,
    ToolNodeSysboxBashState,
)

_WHO = "E0_a1b2c3d4"
_TODO_JSON = json.dumps({"items": [{"who": _WHO, "what": "feed the cat", "when": "today"}]})


@pytest.mark.unit
def test_route_after_bump_routes_fence_retry_to_llm_fence_retry():
    awaiting_fence = ToolNodeSysboxBashState(
        sandbox_session_id="sess-1",
        awaiting_fence_retry=True,
        messages=[AIMessage(content="I'll resubmit the script")],
    )
    assert route_after_bump(awaiting_fence) == "llm_fence_retry"


@pytest.mark.unit
def test_route_after_llm_with_bash_does_not_route_fence_flag_to_tools():
    awaiting_fence = ToolNodeSysboxBashState(
        sandbox_session_id="sess-1",
        awaiting_fence_retry=True,
        messages=[AIMessage(content="I'll resubmit the script")],
    )
    assert route_after_llm_with_bash(awaiting_fence) == "finalize"


@pytest.mark.unit
def test_route_after_llm_with_bash_tools_vs_finalize():
    with_tool_calls = ToolNodeSysboxBashState(
        sandbox_session_id="sess-1",
        messages=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "bash",
                        "args": {"script": "echo hi"},
                        "id": "call_1",
                        "type": "tool_call",
                    },
                ],
            )
        ],
    )
    assert route_after_llm_with_bash(with_tool_calls) == "run_tools"

    final_only = ToolNodeSysboxBashState(
        sandbox_session_id="sess-1",
        messages=[AIMessage(content=f"# {_WHO}\n- [ ] summary (by today)")],
    )
    assert route_after_llm_with_bash(final_only) == "finalize"


@pytest.mark.unit
def test_validate_result_text_raises_on_missing_who():
    with pytest.raises(PipelineValidationError, match="missing placeholder who token"):
        _validate_result_text_against_json(
            "# no placeholder tokens",
            _TODO_JSON,
            tool_errors=0,
        )


@pytest.mark.unit
def test_validate_result_text_allows_reformulated_what():
    reformulated = f"# {_WHO}\n- [ ] completely different wording (by today)"
    _validate_result_text_against_json(reformulated, _TODO_JSON, tool_errors=0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_policy_exhausted_raises_policy_violation_error():
    state = ToolNodeSysboxBashState(
        sandbox_session_id="sess-1",
        tool_errors=MIN_MAX_TOOL_ERRORS,
        messages=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "bash",
                        "args": {"script": "echo hi"},
                        "id": "call_1",
                        "type": "tool_call",
                    },
                ],
            )
        ],
    )
    assert route_after_llm_with_bash(state) == "policy_exhausted"
    with pytest.raises(PolicyViolationError, match="policy exhausted"):
        await _policy_exhausted(state)
