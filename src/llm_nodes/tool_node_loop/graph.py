"""tool_node_loop subgraph compilation and parent-graph bridge."""

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.errors import (
    PipelinePreconditionError,
    PipelineValidationError,
    PolicyViolationError,
)
from src.logging_setup import get_logger

from ...llm_handle.local import ChatModelProvider, ClientCachePolicy
from ..global_state import GlobalState
from ..placeholder_audit import (
    PLACEHOLDER_LIKE_RE,
    allowlist_from_pii_email,
    audit_placeholder_texts,
    log_placeholder_violations,
)
from ..todo_extract.models import TODOItem, TODOList
from .models import ToolNodeLoopState
from .nodes import get_tool_node_loop_agent_node, get_tool_node_loop_tool_node

logger = get_logger(__name__, __file__)


def _tool_message_failed(msg: ToolMessage) -> bool:
    """True when ToolNode reported a handled tool error (not LLM text).

    String-heuristic only (LangGraph ToolNode error text shape); acceptable course
    limitation — false positives if a tool returns content starting with ``Error``.
    """
    content = msg.content if isinstance(msg.content, str) else str(msg.content)
    return content.startswith("Error") or "ToolInvocationError" in content


async def _bump_tool_policy(state: ToolNodeLoopState) -> dict:
    """After tools: count this round and tool failures (trusted, no LLM)."""
    errors_this_round = 0
    for msg in reversed(state.messages):
        if not isinstance(msg, ToolMessage):
            break
        if _tool_message_failed(msg):
            errors_this_round += 1
    return {
        "tool_round": state.tool_round + 1,
        "tool_errors": state.tool_errors + errors_this_round,
    }


def _last_ai_message(messages: list[BaseMessage]) -> AIMessage | None:
    """Return the last AIMessage, or None if no such message."""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return msg
    return None


def route_after_llm_with_tools(state: ToolNodeLoopState) -> str:
    """Route after llm_with_tools: continue while the last AIMessage has tool_calls; else finalize."""
    last_ai_msg = _last_ai_message(state.messages)
    has_pending_tool_calls = bool(last_ai_msg and last_ai_msg.tool_calls)
    policy_exhausted = (
        state.tool_round >= state.max_tool_rounds or state.tool_errors >= state.max_tool_errors
    )

    if has_pending_tool_calls and policy_exhausted:
        logger.debug(
            "route_after_llm_with_tools: policy stop (tool_round=%s/%s tool_errors=%s/%s pending_tool_calls=%s)",
            state.tool_round,
            state.max_tool_rounds,
            state.tool_errors,
            state.max_tool_errors,
            len(last_ai_msg.tool_calls) if last_ai_msg else 0,
        )
        return "policy_exhausted"

    if has_pending_tool_calls:
        logger.debug(
            "route_after_llm_with_tools: -> tools (tool_round=%s tool_errors=%s tool_calls=%s)",
            state.tool_round,
            state.tool_errors,
            len(last_ai_msg.tool_calls) if last_ai_msg else 0,
        )
        return "tools"

    logger.debug(
        "route_after_llm_with_tools: -> finalize (tool_round=%s tool_errors=%s)",
        state.tool_round,
        state.tool_errors,
    )
    return "finalize"


def _required_who_placeholders(items: list[TODOItem]) -> frozenset[str]:
    """Unique ``who`` values that are E{n}_{salt} placeholders (not UNKNOWN / plain names)."""
    tokens: set[str] = set()
    for item in items:
        who = (item.who or "").strip()
        if who and PLACEHOLDER_LIKE_RE.fullmatch(who):
            tokens.add(who)
    return frozenset(tokens)


def _extract_final_markdown(state: ToolNodeLoopState) -> str:
    """Last AIMessage with text and no pending tool_calls."""
    for msg in reversed(state.messages):
        if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            text = msg.content if isinstance(msg.content, str) else str(msg.content)
            return text.strip()
    raise PipelineValidationError("No final AIMessage without tool_calls in messages")


def _validate_todo_text_against_json(
    todo_text: str,
    todo_list_json: str,
    *,
    tool_errors: int,
) -> None:
    """Trusted gate: every placeholder ``who`` from JSON must appear in todo_text.

    Does not check task count, wording, or ``when`` — reformulation/grouping may differ.
    """
    items = TODOList.model_validate_json(todo_list_json).items
    if not items:
        raise PipelineValidationError("Expected non-empty todo_list_json items before finalize")

    missing = sorted(token for token in _required_who_placeholders(items) if token not in todo_text)
    if missing:
        raise PipelineValidationError(
            "todo_text missing placeholder who token(s): %s" % (", ".join(missing),)
        )

    if tool_errors > 0:
        logger.warning(
            "finalize: accepting todo_text after tool_errors=%s (observe — verify in Phoenix/reducer)",
            tool_errors,
        )


async def _finalize(state: ToolNodeLoopState) -> dict:
    """Extract final markdown and validate against todo_list_json (trusted, no LLM)."""
    todo_text = _extract_final_markdown(state)
    _validate_todo_text_against_json(
        todo_text,
        state.todo_list_json,
        tool_errors=state.tool_errors,
    )
    return {"todo_text": todo_text}


async def _policy_exhausted(state: ToolNodeLoopState) -> dict:
    """Guard node: policy exhausted before a valid final deliverable was produced."""
    last_ai = _last_ai_message(state.messages)
    pending_tool_calls = bool(last_ai and last_ai.tool_calls)
    raise PolicyViolationError(
        "tool_node_loop policy exhausted before deliverable: "
        f"tool_round={state.tool_round}/{state.max_tool_rounds}, "
        f"tool_errors={state.tool_errors}/{state.max_tool_errors}, "
        f"pending_tool_calls={pending_tool_calls}"
    )


async def _audit_placeholders(state: ToolNodeLoopState) -> dict:
    """Deterministic allowlist check after the LLM node (does not read raw emails)."""
    result = audit_placeholder_texts(
        state.todo_list_json,
        state.todo_text,
        allowlist=state.placeholder_allowlist,
    )
    log_placeholder_violations(result, node="tool_node_loop")
    return {}


def build_tool_node_loop_subgraph(
    model: str,
    *,
    chat_model_provider: ChatModelProvider | None = None,
    client_cache_policy: ClientCachePolicy = "cached",
) -> CompiledStateGraph:
    """llm_with_tools ↔ ToolNode loop on ToolNodeLoopState.messages."""
    builder = StateGraph(ToolNodeLoopState)
    builder.add_node(
        "llm_with_tools",
        get_tool_node_loop_agent_node(
            model,
            chat_model_provider=chat_model_provider,
            client_cache_policy=client_cache_policy,
        ),
    )
    builder.add_node("tools", get_tool_node_loop_tool_node())
    builder.add_node("bump_tool_policy", _bump_tool_policy)
    builder.add_node("policy_exhausted", _policy_exhausted)
    builder.add_node("finalize", _finalize)
    builder.add_node("audit_placeholders", _audit_placeholders)

    builder.add_edge(START, "llm_with_tools")
    builder.add_conditional_edges(
        "llm_with_tools",
        route_after_llm_with_tools,
        {"tools": "tools", "policy_exhausted": "policy_exhausted", "finalize": "finalize"},
    )
    builder.add_edge("tools", "bump_tool_policy")
    builder.add_edge("bump_tool_policy", "llm_with_tools")
    builder.add_edge("finalize", "audit_placeholders")
    builder.add_edge("audit_placeholders", END)

    return builder.compile()


def make_tool_node_loop_subgraph_runner(tool_node_loop_graph: CompiledStateGraph):
    """Return a parent-graph node that bridges ``GlobalState`` ↔ ``ToolNodeLoopState``.

    At runtime LangGraph calls the inner function with ``(state, config)``.
    ``config`` is forwarded unchanged to ``tool_node_loop_graph.ainvoke``; see the module
    docstring for how that relates to ``reducer_session``.
    """

    async def run_tool_node_loop_subgraph(
        state: GlobalState,
        config: RunnableConfig,
    ) -> dict:
        if not state.todo_list.items:
            raise PipelinePreconditionError(
                "Expected non-empty todo_list.items before tool_node_loop subgraph"
            )

        todo_list_payload = TODOList.model_validate(state.todo_list).model_dump_json()
        allowlist = allowlist_from_pii_email(state.pii_email)

        sub_result = await tool_node_loop_graph.ainvoke(
            {
                "todo_list_json": todo_list_payload,
                "placeholder_allowlist": allowlist,
            },
            config=config,
        )

        if "todo_text" not in sub_result:
            raise PipelineValidationError(
                "tool_node_loop subgraph result missing required key 'todo_text'. "
                f"Available keys: {sorted(sub_result.keys())}"
            )

        return {
            "todo_text": sub_result["todo_text"],
            "final_result": sub_result["todo_text"],
            "messages": sub_result.get("messages", []),
        }

    return run_tool_node_loop_subgraph
