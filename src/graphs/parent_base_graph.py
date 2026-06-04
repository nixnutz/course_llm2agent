"""Basic graph: extract emails from text, build a TODO list, create markdown."""

from dataclasses import dataclass
from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.llm_nodes.global_state import GlobalState
from src.llm_nodes.pii_email.nodes import get_pii_email_node
from src.llm_nodes.todo_extract.graph import (
    build_todo_extract_subgraph,
    make_todo_extract_subgraph_runner,
)
from src.llm_nodes.todo_markdown.graph import (
    build_todo_markdown_subgraph,
    make_todo_markdown_subgraph_runner,
)
from src.other_nodes.demask.nodes import get_demask_node

SubgraphName = Literal["todo_extract", "todo_markdown"]
_SUBGRAPH_NAMES: tuple[SubgraphName, ...] = ("todo_extract", "todo_markdown")


@dataclass(frozen=True)
class ParentBaseGraph:
    """Parent graph bundle for course notebooks and tracing labs.

    Use ``graph`` (a ``CompiledStateGraph``) for ``ainvoke`` / ``session.ainvoke``.
    This wrapper is not runnable and exists so subgraph diagrams stay reachable
    without calling methods on the compiled parent graph.
    """

    graph: CompiledStateGraph
    _subgraphs: dict[SubgraphName, CompiledStateGraph]

    def get_subgraph(self, name: SubgraphName) -> CompiledStateGraph:
        try:
            return self._subgraphs[name]
        except KeyError as exc:
            raise KeyError(
                f"Unknown subgraph {name!r}; expected one of: {list(_SUBGRAPH_NAMES)}"
            ) from exc


def build_parent_base_graph(model: str) -> ParentBaseGraph:
    """Build and compile the course parent graph plus isolated TODO subgraphs."""
    subgraphs: dict[SubgraphName, CompiledStateGraph] = {
        "todo_extract": build_todo_extract_subgraph(model),
        "todo_markdown": build_todo_markdown_subgraph(model),
    }

    builder = StateGraph(GlobalState)
    builder.add_node("pii_extract_node", get_pii_email_node(model=model))
    builder.add_node(
        "todo_extract_node",
        make_todo_extract_subgraph_runner(subgraphs["todo_extract"]),
    )
    builder.add_node(
        "todo_markdown_node",
        make_todo_markdown_subgraph_runner(subgraphs["todo_markdown"]),
    )
    builder.add_node("demask_node", get_demask_node())
    builder.add_edge(START, "pii_extract_node")
    builder.add_edge("pii_extract_node", "todo_extract_node")
    builder.add_edge("todo_extract_node", "todo_markdown_node")
    builder.add_edge("todo_markdown_node", "demask_node")
    builder.add_edge("demask_node", END)

    return ParentBaseGraph(graph=builder.compile(), _subgraphs=subgraphs)
