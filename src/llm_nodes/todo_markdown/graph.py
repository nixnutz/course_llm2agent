"""TODO markdown subgraph compilation and parent-graph bridge."""

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ..global_state import GlobalState
from ..todo_extract.models import TODOList
from .models import TODOMarkdown, TODOMarkdownState
from .nodes import get_todo_markdown_node


def build_todo_markdown_subgraph(model: str) -> CompiledStateGraph:
    """Compile an isolated graph on ``TODOMarkdownState``."""
    builder = StateGraph(TODOMarkdownState)
    builder.add_node("todo_markdown", get_todo_markdown_node(model))
    builder.add_edge(START, "todo_markdown")
    builder.add_edge("todo_markdown", END)
    return builder.compile()


def make_todo_markdown_subgraph_runner(todo_graph: CompiledStateGraph):
    """Return a parent-graph node that bridges ``GlobalState`` ↔ ``TODOState``.

    At runtime LangGraph calls the inner function with ``(state, config)``.
    ``config`` is forwarded unchanged to ``todo_graph.ainvoke``; see the module
    docstring for how that relates to ``reducer_session``.
    """

    async def run_todo_markdown_subgraph(
        state: GlobalState,
        config: RunnableConfig,
    ) -> dict:
        if not state.todo_list.items:
            raise ValueError("Expected non-empty todo_list.items before TODO markdown subgraph")

        todo_list_payload = TODOList.model_validate(state.todo_list).model_dump_json()

        sub_result = await todo_graph.ainvoke(
            {"todo_list_json": todo_list_payload},
            config=config,
        )

        if "todo_markdown" not in sub_result:
            raise KeyError(
                "TODO markdown subgraph result missing required key 'todo_markdown'. "
                f"Available keys: {sorted(sub_result.keys())}"
            )

        return {
            "todo_markdown": TODOMarkdown.model_validate(sub_result["todo_markdown"]),
            "messages": sub_result.get("messages", []),
        }

    return run_todo_markdown_subgraph
