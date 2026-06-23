"""Composed LangGraph state for multi-node course graphs."""

from typing import Annotated

from langchain_core.messages import BaseMessage
from pydantic import Field

from ..reducer.reducer_session import session_message_reducer
from .base_state import BaseState
from .pii_email.models import PIIEmail
from .todo_extract.models import TODOList
from .todo_markdown.models import TODOMarkdown


class GlobalState(BaseState):
    """``messages`` (reducer-guarded) plus pipeline slices.

    ``final_result`` is the shared demask slot (masked in, restored out). Result bridges
    set it alongside node-specific masked snapshots: ``todo_markdown`` (markdown subgraph)
    or ``todo_text`` (tool-node subgraphs).
    """

    messages: Annotated[list[BaseMessage], session_message_reducer] = Field(default_factory=list)
    pii_email: PIIEmail = Field(default_factory=PIIEmail)
    todo_list: TODOList = Field(default_factory=TODOList)
    final_result: str = Field(default="")
    todo_markdown: TODOMarkdown = Field(default_factory=TODOMarkdown)
    todo_text: str = Field(default="")
