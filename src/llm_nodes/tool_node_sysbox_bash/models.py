import os
from typing import Annotated, Self

from langchain_core.messages import BaseMessage
from pydantic import Field, model_validator

from ...reducer.reducer_session import session_message_reducer
from ..base_state import BaseState
from ..placeholder_audit.models import PlaceholderAllowlist
from ..todo_extract.models import TODOList
from ..tool_node_policy import (
    MIN_MAX_TOOL_ERRORS,
    MIN_MAX_TOOL_ROUNDS,
    compute_max_tool_errors,
    compute_max_tool_rounds_with_headroom,
)

DEFAULT_MAX_SCRIPT_SECONDS = 30


def default_max_script_seconds() -> int:
    raw = os.environ.get("SBASH_DEFAULT_TIMEOUT_SECONDS")
    if raw is None or raw == "":
        return DEFAULT_MAX_SCRIPT_SECONDS
    return max(int(raw), 1)


def item_count(todo_list_json: str) -> int:
    """Number of TODO items (one bash round per item in the lab prompt)."""
    if not todo_list_json.strip():
        return 0
    return len(TODOList.model_validate_json(todo_list_json).items)


def compute_max_tool_rounds(todo_list_json: str) -> int:
    """One bash round per item, plus shared 20% headroom."""
    return compute_max_tool_rounds_with_headroom(item_count(todo_list_json))


class ToolNodeSysboxBashState(BaseState):
    """Subgraph state for the sysbox bash tool loop."""

    todo_list_json: str = Field(default="")
    placeholder_allowlist: PlaceholderAllowlist = Field(
        default_factory=PlaceholderAllowlist, frozen=True
    )
    sandbox_session_id: str | None = Field(default=None)
    graph_invoke_id: str | None = Field(default=None)
    messages: Annotated[list[BaseMessage], session_message_reducer] = Field(default_factory=list)

    transport_fence_retry_used: bool = Field(default=False)
    awaiting_fence_retry: bool = Field(default=False)

    tool_round: int = Field(default=0)
    tool_errors: int = Field(default=0)
    max_tool_rounds: int = Field(default=MIN_MAX_TOOL_ROUNDS)
    max_tool_errors: int = Field(default=MIN_MAX_TOOL_ERRORS)
    max_script_seconds: int = Field(default_factory=default_max_script_seconds)
    result_text: str = Field(default="")

    @model_validator(mode="after")
    def _derive_tool_policy_limits(self) -> Self:
        if not self.todo_list_json.strip():
            return self
        max_rounds = compute_max_tool_rounds(self.todo_list_json)
        self.max_tool_rounds = max_rounds
        self.max_tool_errors = compute_max_tool_errors(max_rounds)
        cap = default_max_script_seconds()
        if self.max_script_seconds > cap:
            self.max_script_seconds = cap
        return self
