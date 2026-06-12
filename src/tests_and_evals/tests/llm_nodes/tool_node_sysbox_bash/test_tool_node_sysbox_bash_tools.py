"""L1 exemplars for tool_node_sysbox_bash tool result formatting."""

from langchain_core.messages import ToolMessage
import pytest

from src.llm_nodes.tool_node_sysbox_bash.client import ExecResponse, log_exec_observability
from src.llm_nodes.tool_node_sysbox_bash.graph import _bump_tool_policy, _tool_message_failed
from src.llm_nodes.tool_node_sysbox_bash.models import ToolNodeSysboxBashState
from src.llm_nodes.tool_node_sysbox_bash.tools import format_exec_result


def _exec_response(**overrides) -> ExecResponse:
    defaults = {
        "session_id": "sess-1",
        "run_id": "1",
        "stdout": "ok",
        "stderr": "",
        "exit_code": 0,
        "timed_out": False,
        "output_limit_exceeded": False,
        "elapsed_ms": 10,
        "metadata_path": "/tmp/meta.json",
        "metadata": {},
    }
    defaults.update(overrides)
    return ExecResponse(**defaults)


@pytest.mark.unit
def test_log_exec_observability_emits_debug(caplog):
    response = _exec_response(
        metadata={
            "termination_reason": "completed",
            "thread_id": "t-1",
            "tool_call_id": "c1",
        }
    )
    with caplog.at_level("DEBUG"):
        log_exec_observability(response)
    assert any("sandbox exec metadata=" in record.message for record in caplog.records)
    assert any("termination_reason" in record.message for record in caplog.records)


@pytest.mark.unit
def test_format_exec_result_no_error_prefix_on_success():
    content = format_exec_result(_exec_response())
    assert not content.startswith("Error:")
    assert "exit_code=0" in content


@pytest.mark.unit
def test_format_exec_result_prefixes_error_on_nonzero_exit():
    content = format_exec_result(_exec_response(exit_code=7, stderr="boom"))
    assert content.startswith("Error: bash exit_code=7\n\n")
    assert "exit_code=7" in content
    assert "boom" in content


@pytest.mark.unit
def test_format_exec_result_prefixes_error_on_timeout():
    content = format_exec_result(_exec_response(exit_code=124, timed_out=True))
    assert content.startswith("Error: bash timed_out, exit_code=124\n\n")


@pytest.mark.unit
def test_tool_message_failed_counts_prefixed_exec_result():
    content = format_exec_result(_exec_response(exit_code=2))
    msg = ToolMessage(content=content, tool_call_id="c1", name="bash")
    assert _tool_message_failed(msg) is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_bump_tool_policy_increments_on_nonzero_exit():
    content = format_exec_result(_exec_response(exit_code=2))
    state = ToolNodeSysboxBashState(
        sandbox_session_id="sess-1",
        tool_round=0,
        tool_errors=0,
        messages=[ToolMessage(content=content, tool_call_id="c1", name="bash")],
    )
    bumped = await _bump_tool_policy(state)
    assert bumped["tool_errors"] == 1
