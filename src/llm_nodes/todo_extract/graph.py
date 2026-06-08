"""TODO subgraph compilation and parent-graph bridge.

State isolation (bridge)
------------------------
``build_todo_extract_subgraph`` defines a graph on ``TODOState`` only. The bridge
maps ``GlobalState.pii_email.text`` and a derived ``PlaceholderAllowlist`` (no
raw emails) into that subgraph and merges ``todo_list`` plus AI trace ``messages``
back onto ``GlobalState``. The subgraph never sees ``PIIEmail.emails`` or the
parent's human message list.

Build time vs run time
----------------------
Compiling the subgraph in the notebook (cells *before* ``with reducer_session``)
needs no LangGraph ``config`` and no active reducer session — that is structure
only. Every real execution happens later, inside
``await session.ainvoke(parent_graph, state)`` (or
``session.ainvoke(todo_graph, {"text": ..., "placeholder_allowlist": ...})`` when
testing the subgraph alone).

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

from src.errors import PipelinePreconditionError, PipelineValidationError

from ...llm_handle.local import AsyncClientProvider, ClientCachePolicy
from ..global_state import GlobalState
from ..placeholder_audit import (
    allowlist_from_pii_email,
    audit_placeholder_texts,
    log_placeholder_violations,
)
from .models import TODOList, TODOState
from .nodes import get_todo_list_node


async def _audit_todo_extract_placeholders(state: TODOState) -> dict:
    """Deterministic allowlist check after the LLM node (does not read raw emails)."""
    parts: list[str] = []
    for item in state.todo_list.items:
        parts.extend((item.who, item.what, item.when))
    result = audit_placeholder_texts(*parts, allowlist=state.placeholder_allowlist)
    log_placeholder_violations(result, node="todo_extract")
    return {}


def build_todo_extract_subgraph(
    model: str,
    *,
    client_provider: AsyncClientProvider | None = None,
    client_cache_policy: ClientCachePolicy = "cached",
) -> CompiledStateGraph:
    """Compile an isolated graph on ``TODOState`` (no session/config at build time)."""
    builder = StateGraph(TODOState)
    builder.add_node(
        "todo_extract",
        get_todo_list_node(
            model,
            client_provider=client_provider,
            client_cache_policy=client_cache_policy,
        ),
    )
    builder.add_node("audit_placeholders", _audit_todo_extract_placeholders)
    builder.add_edge(START, "todo_extract")
    builder.add_edge("todo_extract", "audit_placeholders")
    builder.add_edge("audit_placeholders", END)
    return builder.compile()


def make_todo_extract_subgraph_runner(todo_graph: CompiledStateGraph):
    """Return a parent-graph node that bridges ``GlobalState`` ↔ ``TODOState``.

    At runtime LangGraph calls the inner function with ``(state, config)``.
    ``config`` is forwarded unchanged to ``todo_graph.ainvoke``; see the module
    docstring for how that relates to ``reducer_session``.
    """

    async def run_todo_extract_subgraph(
        state: GlobalState,
        config: RunnableConfig,
    ) -> dict:
        if not state.pii_email.text:
            raise PipelinePreconditionError(
                "Expected non-empty pii_email.text before TODO subgraph"
            )

        allowlist = allowlist_from_pii_email(state.pii_email)
        sub_result = await todo_graph.ainvoke(
            {
                "text": state.pii_email.text,
                "placeholder_allowlist": allowlist,
            },
            config=config,
        )

        if "todo_list" not in sub_result:
            raise PipelineValidationError(
                "TODO extract subgraph result missing required key 'todo_list'. "
                f"Available keys: {sorted(sub_result.keys())}"
            )

        return {
            "todo_list": TODOList.model_validate(sub_result["todo_list"]),
            "messages": sub_result.get("messages", []),
        }

    return run_todo_extract_subgraph
