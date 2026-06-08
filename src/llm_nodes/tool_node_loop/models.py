from typing import Annotated

from langchain_core.messages import BaseMessage
from pydantic import Field

from ...reducer.reducer_session import session_message_reducer
from ..base_state import BaseState
from ..placeholder_audit.models import PlaceholderAllowlist

# Policy defaults for the tool loop (router reads these in graph.py).
MAX_TOOL_ROUNDS = 5
MAX_TOOL_ERRORS = 3


class ToolNodeLoopState(BaseState):
    """Subgraph state with input, output, and reducer-aware messages."""

    todo_list_json: str = Field(default="")
    placeholder_allowlist: PlaceholderAllowlist = Field(
        default_factory=PlaceholderAllowlist, frozen=True
    )
    todo_text: str = Field(default="")
    messages: Annotated[list[BaseMessage], session_message_reducer] = Field(default_factory=list)

    tool_round: int = Field(default=0, description="How many times the tools node ran.")
    tool_errors: int = Field(default=0, description="How many ToolMessages reported failure.")
