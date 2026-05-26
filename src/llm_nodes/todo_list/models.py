"""Structured output for the TODO list extraction node."""

from typing import Annotated

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

from ...reducer.reducer_session import session_message_reducer


class TODOItem(BaseModel):
    """One extracted task (who / what / when)."""

    who: str = Field(default="")
    what: str = Field(default="")
    when: str = Field(default="")


class TODOList(BaseModel):
    """Collection of ``TODOItem`` rows from the LLM."""

    items: list[TODOItem] = Field(default_factory=list)


class TODOState(BaseModel):
    """Subgraph-only state: bridge passes ``text`` in; no ``pii_email`` or parent ``messages``."""

    text: str = Field(default="")
    todo_list: TODOList = Field(default_factory=TODOList)
    messages: Annotated[list[BaseMessage], session_message_reducer] = Field(default_factory=list)
