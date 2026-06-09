import math
from typing import Annotated, Self

from langchain_core.messages import BaseMessage
from pydantic import Field, model_validator

from ...reducer.reducer_session import session_message_reducer
from ..base_state import BaseState
from ..placeholder_audit.models import PlaceholderAllowlist
from ..todo_extract.models import TODOList

MIN_MAX_TOOL_ROUNDS = 2
MIN_MAX_TOOL_ERRORS = 1
TOOL_ROUND_TOLERANCE_FACTOR = 1.20
TOOL_ERROR_BUDGET_FRACTION = 0.10


def unique_who_count(todo_list_json: str) -> int:
    """Count distinct non-empty ``who`` values in the TODO JSON."""
    if not todo_list_json.strip():
        return 0
    items = TODOList.model_validate_json(todo_list_json).items
    return len({(item.who or "").strip() for item in items if (item.who or "").strip()})


def compute_max_tool_rounds(todo_list_json: str) -> int:
    """One greet per unique ``who``, plus 20% headroom when the LLM misses uniqueness."""
    unique_who = unique_who_count(todo_list_json)
    base = max(unique_who, 1)
    with_tolerance = math.ceil(base * TOOL_ROUND_TOLERANCE_FACTOR)
    return max(MIN_MAX_TOOL_ROUNDS, with_tolerance)


def compute_max_tool_errors(max_tool_rounds: int) -> int:
    """Up to 10% of ``max_tool_rounds`` tool failures before policy stop."""
    budget = math.floor(max_tool_rounds * TOOL_ERROR_BUDGET_FRACTION)
    return max(MIN_MAX_TOOL_ERRORS, budget)


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
    max_tool_rounds: int = Field(
        default=MIN_MAX_TOOL_ROUNDS,
        description="Policy cap on tool rounds (derived from unique who in todo_list_json).",
    )
    max_tool_errors: int = Field(
        default=MIN_MAX_TOOL_ERRORS,
        description="Policy cap on tool failures (derived from max_tool_rounds).",
    )

    @model_validator(mode="after")
    def _derive_tool_policy_limits(self) -> Self:
        if not self.todo_list_json.strip():
            return self
        max_rounds = compute_max_tool_rounds(self.todo_list_json)
        return self.model_copy(
            update={
                "max_tool_rounds": max_rounds,
                "max_tool_errors": compute_max_tool_errors(max_rounds),
            }
        )
