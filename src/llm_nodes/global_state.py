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

    ``todo_markdown`` is the parent-graph markdown output; ``todo_text`` is interim
    Session-6 output from ``tool_node_loop`` (see TODO on ``todo_text``).
    """

    messages: Annotated[list[BaseMessage], session_message_reducer] = Field(default_factory=list)
    pii_email: PIIEmail = Field(default_factory=PIIEmail)
    todo_list: TODOList = Field(default_factory=TODOList)
    todo_markdown: TODOMarkdown = Field(default_factory=TODOMarkdown)
    # TODO(session6): ``todo_text`` duplicates ``todo_markdown.markdown`` until the parent
    # graph uses ``tool_node_loop``; remove ``todo_text`` after unification.
    todo_text: str = Field(default="")
