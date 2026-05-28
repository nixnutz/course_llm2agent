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
    """``messages`` (reducer-guarded) plus ``pii_email``, ``todo_list``, and ``todo_markdown`` slices."""

    messages: Annotated[list[BaseMessage], session_message_reducer] = Field(default_factory=list)
    pii_email: PIIEmail = Field(default_factory=PIIEmail)
    todo_list: TODOList = Field(default_factory=TODOList)
    todo_markdown: TODOMarkdown = Field(default_factory=TODOMarkdown)
