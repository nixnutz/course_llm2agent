"""Shared tool-round policy helpers for tool-node subgraphs."""

import math

MIN_MAX_TOOL_ROUNDS = 3
MIN_MAX_TOOL_ERRORS = 3
TOOL_ROUND_TOLERANCE_FACTOR = 1.20
TOOL_ERROR_BUDGET_FRACTION = 0.10


def compute_max_tool_rounds_with_headroom(base: int) -> int:
    """Policy cap from a workload base count plus 20% headroom."""
    normalized = max(base, 1)
    with_tolerance = math.ceil(normalized * TOOL_ROUND_TOLERANCE_FACTOR)
    return max(MIN_MAX_TOOL_ROUNDS, with_tolerance)


def compute_max_tool_errors(max_tool_rounds: int) -> int:
    """Up to 10% of ``max_tool_rounds`` tool failures before policy stop."""
    budget = math.floor(max_tool_rounds * TOOL_ERROR_BUDGET_FRACTION)
    return max(MIN_MAX_TOOL_ERRORS, budget)
