"""Tools for the tool_node_loop subgraph (used by bind_tools and ToolNode)."""

from langchain_core.tools import tool


@tool
def greet(who: str, greeting: str = "Salve") -> str:
    """Greet one person from the task list.

    Args:
        who: The ``who`` field from the JSON (placeholder token or name). Required.
        greeting: Short greeting prefix. Optional.
    """
    return f"{greeting}, {who}!"


TOOLS = [greet]
