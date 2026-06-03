"""Structured output for the TODO list extraction node."""

from typing import Annotated

from langchain_core.messages import BaseMessage
from pydantic import Field

from ...reducer.reducer_session import session_message_reducer
from ..base_state import BaseState
from ..placeholder_audit.models import PlaceholderAllowlist


class TODOItem(BaseState):
    """One extracted task (who / what / when)."""

    who: str = Field(default="")
    what: str = Field(default="")
    when: str = Field(default="")


class TODOList(BaseState):
    """Collection of ``TODOItem`` rows from the LLM."""

    items: list[TODOItem] = Field(default_factory=list)


class TODOState(BaseState):
    """Subgraph-only state: bridge passes ``text`` and ``placeholder_allowlist`` in."""

    text: str = Field(default="", frozen=True)
    placeholder_allowlist: PlaceholderAllowlist = Field(
        default_factory=PlaceholderAllowlist, frozen=True
    )
    todo_list: TODOList = Field(default_factory=TODOList)
    messages: Annotated[list[BaseMessage], session_message_reducer] = Field(default_factory=list)
