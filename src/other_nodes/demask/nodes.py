"""LangGraph node: restore PII placeholders in TODO markdown (trusted, no LLM).

Future trusted egress boundary for strict error policy — see ADR 0012.
"""

from langchain_core.messages import AIMessage

from src.errors import PipelinePreconditionError
from src.llm_nodes.global_state import GlobalState
from src.llm_nodes.pii_email.mask import demask_pii_emails
from src.llm_nodes.todo_markdown.models import TODOMarkdown


async def demask_todo_markdown_node(state: GlobalState) -> dict:
    """Replace ``E{n}_{salt}`` tokens in ``todo_markdown`` using ``pii_email`` vault data."""
    if not state.todo_markdown.markdown:
        raise PipelinePreconditionError("Expected non-empty todo_markdown.markdown before demask")

    restored = demask_pii_emails(state.todo_markdown.markdown, state.pii_email)
    # AIMessage keeps demask visible in Phoenix/reducer traces (course compromise).
    return {
        "todo_markdown": TODOMarkdown(markdown=restored),
        "messages": [AIMessage(content=restored)],
    }


def get_demask_node():
    """Return the async callable for ``StateGraph.add_node(..., get_demask_node())``."""
    return demask_todo_markdown_node
