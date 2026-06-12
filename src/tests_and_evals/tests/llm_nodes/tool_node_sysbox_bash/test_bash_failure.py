"""L1 exemplars for transport-syntax failure classification."""

import pytest

from src.llm_nodes.tool_node_sysbox_bash.bash_failure import (
    format_transport_retry_offer,
    is_transport_syntax_failure,
)
from src.llm_nodes.tool_node_sysbox_bash.client import ExecResponse


def _exec_response(**overrides) -> ExecResponse:
    defaults = {
        "session_id": "sess-1",
        "run_id": "1",
        "stdout": "",
        "stderr": "",
        "exit_code": 2,
        "timed_out": False,
        "output_limit_exceeded": False,
        "elapsed_ms": 10,
        "metadata_path": "/tmp/meta.json",
        "metadata": {},
    }
    defaults.update(overrides)
    return ExecResponse(**defaults)


_SESSION7_STDERR = (
    'script.sh: line 21: unexpected EOF while looking for matching `"\''
)


@pytest.mark.unit
@pytest.mark.parametrize(
    "stderr",
    [
        _SESSION7_STDERR,
        "script.sh: line 22: syntax error: unexpected end of file",
        "script.sh: line 4: syntax error near unexpected token `)'",
        (
            "script.sh: line 8: warning: here-document at line 8 "
            "delimited by end-of-file (wanted `EOF')"
        ),
    ],
)
def test_is_transport_syntax_failure_matches_patterns(stderr: str):
    assert is_transport_syntax_failure(_exec_response(stderr=stderr)) is True


@pytest.mark.unit
@pytest.mark.parametrize(
    "overrides",
    [
        {"exit_code": 1, "stderr": "command not found"},
        {"exit_code": 2, "stderr": "command not found"},
        {"exit_code": 2, "stderr": "permission denied"},
        {"exit_code": 0, "stderr": _SESSION7_STDERR},
        {"exit_code": 2, "timed_out": True, "stderr": _SESSION7_STDERR},
    ],
)
def test_is_transport_syntax_failure_negative_cases(overrides: dict):
    assert is_transport_syntax_failure(_exec_response(**overrides)) is False


@pytest.mark.unit
def test_format_transport_retry_offer_uses_transport_prefix():
    offer = format_transport_retry_offer(_exec_response(stderr=_SESSION7_STDERR))
    assert offer.startswith("Transport retry:")
    assert _SESSION7_STDERR in offer
    assert "no tool_calls" in offer
