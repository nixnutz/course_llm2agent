"""LangGraph nodes for the tool_node_loop subgraph (agent + LangGraph ToolNode).

TODO (deferred decisions — course WIP, no ADR yet)
-------------------------------------------------
1. **Runtime boundary (current)** — transport/env wiring for ``ChatOpenAI`` is
   delegated to ``llm_handle.local`` via ``ChatModelProvider``. This node keeps
   domain ownership of ``bind_tools(...)`` and prompt policy.

2. **Tool surface** — ``greet`` in ``tools.py`` is a symbolic ``@tool`` demo. A later
   ``tool_custom_loop`` package may swap ToolNode for a custom executor without
   changing this reference loop.

3. **Tool-loop exit policy** — ``route_after_agent`` covers max rounds/errors plus
   ``tool_calls``; not yet: wall-clock budget, human-in-the-loop, per-tool caps.
"""

from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import ToolNode

from src.errors import PipelinePreconditionError

from ...llm_handle.local import (
    ChatModelProvider,
    ClientCachePolicy,
    make_chat_openai_model_provider,
)
from .models import ToolNodeLoopState
from .prompts import _tool_node_loop_prompt
from .tools import TOOLS


class ToolNodeLoopAgent:
    """LLM node with tools bound; may return tool_calls for LangGraph ToolNode."""

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

    async def __call__(self, state: ToolNodeLoopState) -> dict:
        if not state.todo_list_json:
            raise PipelinePreconditionError("Expected non-empty todo_list_json")

        prompt_value = self._template.invoke({"input": state.todo_list_json})
        system_and_user = prompt_value.to_messages()
        # Keep system+user on every turn; append tool-loop history after round 1.
        messages = system_and_user + list(state.messages)
        response = await self._llm.ainvoke(messages)
        return {"messages": [response]}


def get_tool_node_loop_agent_node(
    model: str,
    chat_model_provider: ChatModelProvider | None = None,
    client_cache_policy: ClientCachePolicy = "cached",
):
    return ToolNodeLoopAgent(
        model=model,
        template=_tool_node_loop_prompt,
        chat_model_provider=chat_model_provider,
        client_cache_policy=client_cache_policy,
    )


# Tool execution (LangGraph prebuilt ToolNode).
# handle_tool_errors=True  → Observe (ADR 0012): error text in ToolMessage, loop continues.
# handle_tool_errors=False → Fail-fast: exception aborts the subgraph run.
HANDLE_TOOL_ERRORS = True
_TOOL_NODE = ToolNode(TOOLS, handle_tool_errors=HANDLE_TOOL_ERRORS)


def get_tool_node_loop_tool_node() -> ToolNode:
    return _TOOL_NODE
