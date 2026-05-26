"""TODO subgraph compilation and parent-graph bridge.

State isolation (bridge)
------------------------
``build_todo_subgraph`` defines a graph on ``TODOState`` only. The bridge from
``make_todo_subgraph_runner`` maps ``GlobalState.pii_email.text`` into that
subgraph and merges ``todo_list`` plus AI trace ``messages`` back onto
``GlobalState``. The subgraph never sees ``pii_email`` or the parent's human
message list.

Build time vs run time
----------------------
Compiling the subgraph in the notebook (cells *before* ``with reducer_session``)
needs no LangGraph ``config`` and no active reducer session — that is structure
only. Every real execution happens later, inside
``await session.ainvoke(parent_graph, state)`` (or
``session.ainvoke(todo_graph, {"text": ...})`` when testing the subgraph alone).

LangGraph ``config`` (thread_id, tracing, checkpoints)
------------------------------------------------------
``ReducerSession.ainvoke`` merges ``configurable.thread_id`` for the parent run.
LangGraph passes the same ``RunnableConfig`` into each parent node, including the
bridge. The bridge **must** forward that ``config`` to ``todo_graph.ainvoke`` so
the nested run uses the same conversation id as the outer graph. Omitting it
does not break ``session_message_reducer`` (see below) but can desynchronise
LangGraph checkpoints and tracing from the session's ``thread_id``.

Reducer / vault (``reducer_session`` context)
---------------------------------------------
``session_message_reducer`` does not read ``config``; it resolves the active
reducer via ``contextvars`` set by ``with reducer_session(...)``. While the
parent ``ainvoke`` runs on that OS thread, vault hooks also apply to ``messages``
merges inside the subgraph. Forwarding ``config`` and keeping the session block
are complementary: same run, two mechanisms.

Further detail: ``src/reducer/reducer_session.py``.
"""

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ..global_state import GlobalState
from .models import TODOList, TODOState
from .nodes import get_todo_list_node


def build_todo_subgraph(model: str) -> CompiledStateGraph:
    """Compile an isolated graph on ``TODOState`` (no session/config at build time)."""
    builder = StateGraph(TODOState)
    builder.add_node("todo_extract", get_todo_list_node(model))
    builder.add_edge(START, "todo_extract")
    builder.add_edge("todo_extract", END)
    return builder.compile()


def make_todo_subgraph_runner(todo_graph: CompiledStateGraph):
    """Return a parent-graph node that bridges ``GlobalState`` ↔ ``TODOState``.

    At runtime LangGraph calls the inner function with ``(state, config)``.
    ``config`` is forwarded unchanged to ``todo_graph.ainvoke``; see the module
    docstring for how that relates to ``reducer_session``.
    """

    async def run_todo_subgraph(
        state: GlobalState,
        config: RunnableConfig,
    ) -> dict:
        if not state.pii_email.text:
            raise ValueError("Expected non-empty pii_email.text before TODO subgraph")

        sub_result = await todo_graph.ainvoke(
            {"text": state.pii_email.text},
            config=config,
        )
        if isinstance(sub_result, dict):
            todo_list = sub_result.get("todo_list")
            messages = sub_result.get("messages", [])
        else:
            todo_list = sub_result.todo_list
            messages = sub_result.messages

        if todo_list is not None and not isinstance(todo_list, TODOList):
            todo_list = TODOList.model_validate(todo_list)

        return {
            "todo_list": todo_list or TODOList(),
            "messages": messages,
        }

    return run_todo_subgraph
