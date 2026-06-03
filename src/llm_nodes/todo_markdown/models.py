from typing import Annotated

from langchain_core.messages import BaseMessage
from pydantic import Field

from ...reducer.reducer_session import session_message_reducer
from ..base_state import BaseState
from ..placeholder_audit.models import PlaceholderAllowlist


class TODOMarkdown(BaseState):
    """Structured TODO markdown output."""

    markdown: str = Field(default="")


class TODOMarkdownState(BaseState):
    """Subgraph state with input, output, and reducer-aware messages."""

    todo_list_json: str = Field(default="")
    placeholder_allowlist: PlaceholderAllowlist = Field(
        default_factory=PlaceholderAllowlist, frozen=True
    )
    todo_markdown: TODOMarkdown = Field(default_factory=TODOMarkdown)
    messages: Annotated[list[BaseMessage], session_message_reducer] = Field(default_factory=list)
