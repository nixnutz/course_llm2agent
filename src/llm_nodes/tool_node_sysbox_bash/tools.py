"""Tools for the tool_node_sysbox_bash subgraph (LLM schema + exec formatting)."""

from langchain_core.tools import tool

from .client import ExecResponse


@tool
def bash(script: str) -> str:
    """Run a bash script in the per-invoke sandbox session.

    Args:
        script: Bash script body to execute.
    """
    # Executed by the custom run_tools node, not by ToolNode.
    return ""


def _sandbox_run_failed(response: ExecResponse) -> bool:
    if response.timed_out or response.output_limit_exceeded:
        return True
    return response.exit_code is not None and response.exit_code != 0


def _sandbox_failure_summary(response: ExecResponse) -> str:
    parts: list[str] = []
    if response.timed_out:
        parts.append("timed_out")
    if response.output_limit_exceeded:
        parts.append("output_limit_exceeded")
    if response.exit_code is not None and response.exit_code != 0:
        parts.append(f"exit_code={response.exit_code}")
    return ", ".join(parts) if parts else "sandbox run failed"


def format_exec_result(response: ExecResponse) -> str:
    """Format a sandbox exec response for the LLM ToolMessage.

    Non-zero exit (and timeout/output-cap failures) are prefixed with ``Error:`` so
    ``_tool_message_failed`` in the subgraph policy layer increments ``tool_errors``.
    """
    lines = [
        f"exit_code={response.exit_code}",
        f"timed_out={str(response.timed_out).lower()}",
        f"output_limit_exceeded={str(response.output_limit_exceeded).lower()}",
        f"elapsed_ms={response.elapsed_ms}",
        "--- stdout ---",
        response.stdout,
        "--- stderr ---",
        response.stderr,
    ]
    body = "\n".join(lines)
    if _sandbox_run_failed(response):
        return f"Error: bash {_sandbox_failure_summary(response)}\n\n{body}"
    return body


TOOLS = [bash]
