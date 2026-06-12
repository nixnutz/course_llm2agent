"""LangGraph nodes for tool_node_sysbox_bash (llm_with_bash + custom run_tools)."""

from __future__ import annotations

from uuid import uuid4

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from src.errors import PipelinePreconditionError

from ...llm_handle.local import (
    ChatModelProvider,
    ClientCachePolicy,
    make_chat_openai_model_provider,
)
from .client import ExecCorrelation, SandboxClient, SandboxClientError, log_exec_observability
from .models import ToolNodeSysboxBashState
from .prompts import _tool_node_sysbox_bash_prompt
from .tools import TOOLS, format_exec_result


class ToolNodeSysboxBashAgent:
    """LLM-with-tools turn; may return tool_calls for run_tools."""

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
        system_and_user = prompt_value.to_messages()
        messages = system_and_user + list(state.messages)
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


def _last_ai_message(messages: list) -> AIMessage | None:
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return msg
    return None


def _thread_id_from_config(config: RunnableConfig) -> str | None:
    configurable = config.get("configurable") or {}
    thread_id = configurable.get("thread_id")
    return thread_id if isinstance(thread_id, str) else None


def get_run_tools_node(client: SandboxClient):
    """Custom tool executor: reads sandbox_session_id from graph state."""

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
