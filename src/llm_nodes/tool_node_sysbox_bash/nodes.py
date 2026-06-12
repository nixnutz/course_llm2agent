"""LangGraph nodes for tool_node_sysbox_bash (llm_with_bash + custom run_tools)."""

from __future__ import annotations

from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from src.errors import PipelinePreconditionError
from src.logging_setup import get_logger

from ...llm_handle.local import (
    ChatModelProvider,
    ClientCachePolicy,
    make_chat_openai_model_provider,
)
from .bash_failure import format_transport_retry_offer, is_transport_syntax_failure
from .client import ExecCorrelation, SandboxClient, SandboxClientError, log_exec_observability
from .models import ToolNodeSysboxBashState
from .prompts import FENCE_RETRY_SNIPPET, _tool_node_sysbox_bash_prompt
from .script_extract import FENCE_RETRY_TOOL_CALL_ID, extract_bash_fence
from .tools import TOOLS, format_exec_result

logger = get_logger(__name__, __file__)


class ToolNodeSysboxBashAgent:
    """LLM turn with bind_tools; may return tool_calls for run_tools."""

    def __init__(
        self,
        model: str,
        template: ChatPromptTemplate,
        chat_model_provider: ChatModelProvider | None = None,
        client_cache_policy: ClientCachePolicy = "cached",
    ):
        provider = chat_model_provider or make_chat_openai_model_provider(
            model=model,
            client_cache_policy=client_cache_policy,
            temperature=0.0,
        )
        self._llm = provider().bind_tools(TOOLS, parallel_tool_calls=False)
        self._template = template

    async def __call__(self, state: ToolNodeSysboxBashState) -> dict:
        if not state.todo_list_json:
            raise PipelinePreconditionError("Expected non-empty todo_list_json")

        prompt_value = self._template.invoke({"input": state.todo_list_json})
        messages = prompt_value.to_messages() + list(state.messages)
        response = await self._llm.ainvoke(messages)
        return {"messages": [response]}


class ToolNodeFenceRetryAgent:
    """One-shot transport retry: plain LLM (no bind_tools) → markdown bash fence in content."""

    def __init__(
        self,
        model: str,
        template: ChatPromptTemplate,
        chat_model_provider: ChatModelProvider | None = None,
        client_cache_policy: ClientCachePolicy = "cached",
    ):
        provider = chat_model_provider or make_chat_openai_model_provider(
            model=model,
            client_cache_policy=client_cache_policy,
            temperature=0.0,
        )
        self._llm = provider()
        self._template = template

    async def __call__(self, state: ToolNodeSysboxBashState) -> dict:
        if not state.todo_list_json:
            raise PipelinePreconditionError("Expected non-empty todo_list_json")

        logger.debug(
            "fence retry: llm turn without bind_tools tool_round=%s session_id=%s",
            state.tool_round,
            state.sandbox_session_id,
        )
        prompt_value = self._template.invoke({"input": state.todo_list_json})
        messages = (
            prompt_value.to_messages()
            + list(state.messages)
            + [HumanMessage(content=FENCE_RETRY_SNIPPET.strip())]
        )
        response = await self._llm.ainvoke(messages)
        return {"messages": [response]}


def get_tool_node_sysbox_bash_agent_node(
    model: str,
    chat_model_provider: ChatModelProvider | None = None,
    client_cache_policy: ClientCachePolicy = "cached",
):
    return ToolNodeSysboxBashAgent(
        model=model,
        template=_tool_node_sysbox_bash_prompt,
        chat_model_provider=chat_model_provider,
        client_cache_policy=client_cache_policy,
    )


def get_llm_fence_retry_node(
    model: str,
    chat_model_provider: ChatModelProvider | None = None,
    client_cache_policy: ClientCachePolicy = "cached",
):
    return ToolNodeFenceRetryAgent(
        model=model,
        template=_tool_node_sysbox_bash_prompt,
        chat_model_provider=chat_model_provider,
        client_cache_policy=client_cache_policy,
    )


def _last_ai_message(messages: list) -> AIMessage | None:
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return msg
    return None


def _ai_content(last_ai: AIMessage) -> str:
    return last_ai.content if isinstance(last_ai.content, str) else str(last_ai.content or "")


async def _execute_script(
    client: SandboxClient,
    state: ToolNodeSysboxBashState,
    *,
    script: str,
    tool_call_id: str,
) -> str:
    try:
        response = await client.execute_in_session(
            state.sandbox_session_id,
            script=script,
            correlation=ExecCorrelation(
                request_id=str(uuid4()),
                tool_round=state.tool_round,
                tool_call_id=tool_call_id,
            ),
            timeout_seconds=state.max_script_seconds,
        )
        log_exec_observability(response)
        return format_exec_result(response)
    except SandboxClientError as exc:
        return f"Error: {exc}"
    except Exception as exc:
        return f"Error: ToolInvocationError: {exc}"


def get_run_tools_node(client: SandboxClient):
    """Execute bash tool_calls from the last AIMessage (bind_tools transport)."""

    async def run_tools(state: ToolNodeSysboxBashState, config: RunnableConfig) -> dict:
        if not state.sandbox_session_id:
            raise PipelinePreconditionError(
                "Expected sandbox_session_id before run_tools (set by bridge)"
            )

        last_ai = _last_ai_message(state.messages)
        if not last_ai or not last_ai.tool_calls:
            return {}

        tool_messages: list[ToolMessage] = []
        for tool_call in last_ai.tool_calls:
            name = tool_call.get("name")
            tool_call_id = tool_call.get("id") or ""
            if name != "bash":
                tool_messages.append(
                    ToolMessage(
                        content=f"Error: unknown tool {name!r}",
                        tool_call_id=tool_call_id,
                        name=name or "unknown",
                    )
                )
                continue

            args = tool_call.get("args") or {}
            script = args.get("script", "")
            if not isinstance(script, str) or not script.strip():
                tool_messages.append(
                    ToolMessage(
                        content="Error: bash requires non-empty script argument",
                        tool_call_id=tool_call_id,
                        name="bash",
                    )
                )
                continue

            try:
                response = await client.execute_in_session(
                    state.sandbox_session_id,
                    script=script,
                    correlation=ExecCorrelation(
                        request_id=str(uuid4()),
                        tool_round=state.tool_round,
                        tool_call_id=tool_call_id,
                    ),
                    timeout_seconds=state.max_script_seconds,
                )
                log_exec_observability(response)
                if (
                    is_transport_syntax_failure(response)
                    and not state.transport_fence_retry_used
                ):
                    logger.debug(
                        "fence retry: entered after transport syntax failure "
                        "tool_round=%s tool_call_id=%s exit_code=%s session_id=%s",
                        state.tool_round,
                        tool_call_id,
                        response.exit_code,
                        state.sandbox_session_id,
                    )
                    return {
                        "messages": [
                            ToolMessage(
                                content=format_transport_retry_offer(response),
                                tool_call_id=tool_call_id,
                                name="bash",
                            )
                        ],
                        "awaiting_fence_retry": True,
                        "transport_fence_retry_used": True,
                    }
                content = format_exec_result(response)
            except SandboxClientError as exc:
                content = f"Error: {exc}"
            except Exception as exc:
                content = f"Error: ToolInvocationError: {exc}"

            tool_messages.append(
                ToolMessage(content=content, tool_call_id=tool_call_id, name="bash")
            )

        return {"messages": tool_messages}

    return run_tools


def get_run_fence_retry_node(client: SandboxClient):
    """Extract ```bash fence from last AIMessage and execute (transport-retry path)."""

    async def run_fence_retry(state: ToolNodeSysboxBashState, config: RunnableConfig) -> dict:
        if not state.sandbox_session_id:
            raise PipelinePreconditionError(
                "Expected sandbox_session_id before run_fence_retry (set by bridge)"
            )

        logger.debug(
            "fence retry: executing fenced script tool_round=%s session_id=%s",
            state.tool_round,
            state.sandbox_session_id,
        )
        last_ai = _last_ai_message(state.messages)
        if not last_ai:
            return {"awaiting_fence_retry": False}

        script = extract_bash_fence(_ai_content(last_ai))
        if not script:
            return {
                "messages": [
                    ToolMessage(
                        content="Error: transport retry requires a single bash fence",
                        tool_call_id=FENCE_RETRY_TOOL_CALL_ID,
                        name="bash",
                    )
                ],
                "awaiting_fence_retry": False,
            }

        content = await _execute_script(
            client,
            state,
            script=script,
            tool_call_id=FENCE_RETRY_TOOL_CALL_ID,
        )
        return {
            "messages": [
                ToolMessage(
                    content=content,
                    tool_call_id=FENCE_RETRY_TOOL_CALL_ID,
                    name="bash",
                )
            ],
            "awaiting_fence_retry": False,
        }

    return run_fence_retry
