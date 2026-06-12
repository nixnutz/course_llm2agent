"""Classify sandbox exec failures for transport-retry (quote/heredoc parse heuristics)."""

from __future__ import annotations

from .client import ExecResponse

TRANSPORT_RETRY_PREFIX = "Transport retry:"


def is_transport_syntax_failure(response: ExecResponse) -> bool:
    """True when exit_code==2 and stderr matches known bash parse/quote patterns."""
    if response.exit_code != 2:
        return False
    if response.timed_out or response.output_limit_exceeded:
        return False
    stderr = response.stderr or ""
    if "unexpected EOF while looking for matching" in stderr:
        return True
    if "syntax error: unexpected end of file" in stderr:
        return True
    if "syntax error near unexpected token" in stderr:
        return True
    if "here-document at line" in stderr and "delimited by end-of-file" in stderr:
        return True
    return False


def format_transport_retry_offer(response: ExecResponse) -> str:
    """ToolMessage body for the one-shot fence retry (not counted as tool_errors)."""
    stderr_excerpt = (response.stderr or "").strip()
    return (
        f"{TRANSPORT_RETRY_PREFIX} bash parse/quote failure (likely tool JSON escaping).\n"
        "Resubmit the full script as a single ```bash fenced block only — no tool_calls.\n\n"
        "--- stderr ---\n"
        f"{stderr_excerpt}"
    )
