"""tool_node_sysbox_bash subgraph compilation and parent-graph bridge."""

from __future__ import annotations

import os
from uuid import uuid4

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
from .client import SandboxClient, SessionCorrelation
from .models import ToolNodeSysboxBashState
from .nodes import (
    get_llm_fence_retry_node,
    get_run_fence_retry_node,
    get_run_tools_node,
    get_tool_node_sysbox_bash_agent_node,
)

logger = get_logger(__name__, __file__)

SUBGRAPH_NAME = "tool_node_sysbox_bash"

# Transport-retry side path (session7): run_tools → bump → llm_fence_retry → run_fence_retry
# → bump → llm_with_bash. Happy path stays bind_tools + run_tools.
#
# Future: failure taxonomy beyond transport syntax (runtime vs timeout weighting).


def _tool_message_failed(msg: ToolMessage) -> bool:
    content = msg.content if isinstance(msg.content, str) else str(msg.content)
    if content.startswith("Transport retry:"):
        return False
    return content.startswith("Error") or "ToolInvocationError" in content


async def _bump_tool_policy(state: ToolNodeSysboxBashState) -> dict:
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
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return msg
    return None


def _is_policy_exhausted(state: ToolNodeSysboxBashState) -> bool:
    return (
        state.tool_round >= state.max_tool_rounds or state.tool_errors >= state.max_tool_errors
    )


def route_after_llm_with_bash(state: ToolNodeSysboxBashState) -> str:
    """Happy-path LLM turn: tool_calls → run_tools, else finalize."""
    last_ai_msg = _last_ai_message(state.messages)
    has_pending_tool_calls = bool(last_ai_msg and last_ai_msg.tool_calls)

    if has_pending_tool_calls and _is_policy_exhausted(state):
        return "policy_exhausted"
    if has_pending_tool_calls:
        return "run_tools"
    return "finalize"


def route_after_bump(state: ToolNodeSysboxBashState) -> str:
    """After bump: transport-retry offer → llm_fence_retry, else main LLM loop."""
    if state.awaiting_fence_retry:
        if _is_policy_exhausted(state):
            return "policy_exhausted"
        return "llm_fence_retry"
    return "llm_with_bash"


def _required_who_placeholders(items: list[TODOItem]) -> frozenset[str]:
    tokens: set[str] = set()
    for item in items:
        who = (item.who or "").strip()
        if who and PLACEHOLDER_LIKE_RE.fullmatch(who):
            tokens.add(who)
    return frozenset(tokens)


def _extract_final_markdown(state: ToolNodeSysboxBashState) -> str:
    for msg in reversed(state.messages):
        if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            text = msg.content if isinstance(msg.content, str) else str(msg.content)
            return text.strip()
    raise PipelineValidationError("No final AIMessage without tool_calls in messages")


def _validate_result_text_against_json(
    result_text: str,
    todo_list_json: str,
    *,
    tool_errors: int,
) -> None:
    items = TODOList.model_validate_json(todo_list_json).items
    if not items:
        raise PipelineValidationError("Expected non-empty todo_list_json items before finalize")

    missing = sorted(
        token for token in _required_who_placeholders(items) if token not in result_text
    )
    if missing:
        raise PipelineValidationError(
            "result_text missing placeholder who token(s): %s" % (", ".join(missing),)
        )

    if tool_errors > 0:
        logger.warning(
            "finalize: accepting result_text after tool_errors=%s (observe — verify in Phoenix/reducer)",
            tool_errors,
        )


async def _finalize(state: ToolNodeSysboxBashState) -> dict:
    result_text = _extract_final_markdown(state)
    _validate_result_text_against_json(
        result_text,
        state.todo_list_json,
        tool_errors=state.tool_errors,
    )
    return {"result_text": result_text}


async def _policy_exhausted(state: ToolNodeSysboxBashState) -> dict:
    last_ai = _last_ai_message(state.messages)
    pending_tool_calls = bool(last_ai and last_ai.tool_calls)
    raise PolicyViolationError(
        "tool_node_sysbox_bash policy exhausted before deliverable: "
        f"tool_round={state.tool_round}/{state.max_tool_rounds}, "
        f"tool_errors={state.tool_errors}/{state.max_tool_errors}, "
        f"pending_tool_calls={pending_tool_calls}"
    )


async def _audit_placeholders(state: ToolNodeSysboxBashState) -> dict:
    result = audit_placeholder_texts(
        state.todo_list_json,
        state.result_text,
        allowlist=state.placeholder_allowlist,
    )
    log_placeholder_violations(result, node=SUBGRAPH_NAME)
    return {}


def _thread_id_from_config(config: RunnableConfig) -> str | None:
    configurable = config.get("configurable") or {}
    thread_id = configurable.get("thread_id")
    return thread_id if isinstance(thread_id, str) else None


def build_tool_node_sysbox_bash_subgraph(
    model: str,
    *,
    sandbox_client: SandboxClient | None = None,
    chat_model_provider: ChatModelProvider | None = None,
    client_cache_policy: ClientCachePolicy = "cached",
) -> CompiledStateGraph:
    if sandbox_client is None:
        base_url = os.environ.get("SBASH_BASE_URL")
        if not base_url:
            raise PipelinePreconditionError(
                "Missing SBASH_BASE_URL or sandbox_client for tool_node_sysbox_bash subgraph"
            )
        sandbox_client = SandboxClient(base_url)
    client = sandbox_client

    builder = StateGraph(ToolNodeSysboxBashState)
    builder.add_node(
        "llm_with_bash",
        get_tool_node_sysbox_bash_agent_node(
            model,
            chat_model_provider=chat_model_provider,
            client_cache_policy=client_cache_policy,
        ),
    )
    builder.add_node("run_tools", get_run_tools_node(client))
    builder.add_node(
        "llm_fence_retry",
        get_llm_fence_retry_node(
            model,
            chat_model_provider=chat_model_provider,
            client_cache_policy=client_cache_policy,
        ),
    )
    builder.add_node("run_fence_retry", get_run_fence_retry_node(client))
    builder.add_node("bump_tool_policy", _bump_tool_policy)
    builder.add_node("policy_exhausted", _policy_exhausted)
    builder.add_node("finalize", _finalize)
    builder.add_node("audit_placeholders", _audit_placeholders)

    builder.add_edge(START, "llm_with_bash")
    builder.add_conditional_edges(
        "llm_with_bash",
        route_after_llm_with_bash,
        {
            "run_tools": "run_tools",
            "policy_exhausted": "policy_exhausted",
            "finalize": "finalize",
        },
    )
    builder.add_edge("run_tools", "bump_tool_policy")
    builder.add_conditional_edges(
        "bump_tool_policy",
        route_after_bump,
        {
            "llm_fence_retry": "llm_fence_retry",
            "llm_with_bash": "llm_with_bash",
            "policy_exhausted": "policy_exhausted",
        },
    )
    builder.add_edge("llm_fence_retry", "run_fence_retry")
    builder.add_edge("run_fence_retry", "bump_tool_policy")
    builder.add_edge("finalize", "audit_placeholders")
    builder.add_edge("audit_placeholders", END)
    builder.add_edge("policy_exhausted", END)

    return builder.compile()


def make_tool_node_sysbox_bash_subgraph_runner(
    tool_node_sysbox_bash_graph: CompiledStateGraph,
    *,
    sandbox_client: SandboxClient | None = None,
):
    """Bridge GlobalState ↔ ToolNodeSysboxBashState; owns sandbox session lifecycle."""

    async def run_tool_node_sysbox_bash_subgraph(
        state: GlobalState,
        config: RunnableConfig,
    ) -> dict:
        if not state.todo_list.items:
            raise PipelinePreconditionError(
                "Expected non-empty todo_list.items before tool_node_sysbox_bash subgraph"
            )

        base_url = os.environ.get("SBASH_BASE_URL")
        if not base_url:
            raise PipelinePreconditionError("Missing SBASH_BASE_URL")

        owns_client = sandbox_client is None
        client = sandbox_client or SandboxClient(base_url)
        try:
            graph_invoke_id = str(uuid4())
            session_correlation = SessionCorrelation(
                graph_invoke_id=graph_invoke_id,
                thread_id=_thread_id_from_config(config),
            )

            session_id = (
                await client.start_session(correlation=session_correlation)
            ).session_id

            todo_list_payload = TODOList.model_validate(state.todo_list).model_dump_json()
            allowlist = allowlist_from_pii_email(state.pii_email)

            try:
                sub_result = await tool_node_sysbox_bash_graph.ainvoke(
                    {
                        "todo_list_json": todo_list_payload,
                        "placeholder_allowlist": allowlist,
                        "sandbox_session_id": session_id,
                        "graph_invoke_id": graph_invoke_id,
                    },
                    config=config,
                )
            finally:
                await client.end_session(session_id)

            if "result_text" not in sub_result:
                raise PipelineValidationError(
                    "tool_node_sysbox_bash subgraph result missing required key 'result_text'. "
                    f"Available keys: {sorted(sub_result.keys())}"
                )

            return {
                "todo_text": sub_result["result_text"],
                "messages": sub_result.get("messages", []),
            }
        finally:
            if owns_client:
                await client.aclose()

    return run_tool_node_sysbox_bash_subgraph
