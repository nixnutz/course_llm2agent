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


def format_exec_result(response: ExecResponse) -> str:
    """Format a sandbox exec response for the LLM ToolMessage."""
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
    return "\n".join(lines)


TOOLS = [bash]
