"""LangGraph node: restore PII placeholders in ``final_result`` (trusted, no LLM).

Future trusted egress boundary for strict error policy — see ADR 0012.
"""

from langchain_core.messages import AIMessage

from src.errors import PipelinePreconditionError
from src.llm_nodes.global_state import GlobalState
from src.llm_nodes.pii_email.mask import demask_pii_emails


async def demask_final_result_node(state: GlobalState) -> dict:
    """Replace ``E{n}_{salt}`` tokens in ``final_result`` using ``pii_email`` vault data."""
    if not state.final_result:
        raise PipelinePreconditionError("Expected non-empty final_result before demask")

    restored = demask_pii_emails(state.final_result, state.pii_email)
    # AIMessage keeps demask visible in Phoenix/reducer traces (course compromise).
    return {
        "final_result": restored,
        "messages": [AIMessage(content=restored)],
    }


def get_demask_node():
    """Return the async callable for ``StateGraph.add_node(..., get_demask_node())``."""
    return demask_final_result_node
