"""Composed LangGraph state for multi-node course graphs."""

from typing import Annotated

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

from ..reducer.reducer_session import session_message_reducer
from .pii_email.models import PIIEmail
from .todo_list.models import TODOList


class GlobalState(BaseModel):
    """``messages`` (reducer-guarded) plus ``pii_email`` and ``todo_list`` slices."""

    messages: Annotated[list[BaseMessage], session_message_reducer] = Field(default_factory=list)
    pii_email: PIIEmail = Field(default_factory=PIIEmail)
    todo_list: TODOList = Field(default_factory=TODOList)
