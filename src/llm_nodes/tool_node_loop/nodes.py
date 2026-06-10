"""LangGraph nodes for the tool_node_loop subgraph (llm_with_tools + ToolNode).

Current scope and extension points
----------------------------------
1. **Runtime boundary (current)** — transport/env wiring for ``ChatOpenAI`` is
   delegated to ``llm_handle.local`` via ``ChatModelProvider``. This node owns
   domain behavior such as ``bind_tools(...)`` and prompt policy.

2. **Tool surface (symbolic by design)** — ``greet`` in ``tools.py`` is a minimal
   ``@tool`` demo. The same loop shape can later run with a custom executor
   (for example bash/sysbox) without changing the core ``llm_with_tools`` contract.

3. **Exit/control policy (extensible)** — ``route_after_llm_with_tools`` already
   enforces round/error limits plus ``tool_calls`` flow control. The same framework
   can be extended with, for example, a runtime budget, human-in-the-loop gates,
   and per-tool caps.
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
    """LLM-with-tools turn for the tool_node_loop subgraph; may return tool_calls for ToolNode."""

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
        # One tool_call per LLM turn (course default): simpler Phoenix traces, easier
        # tool_round/error policy, and steadier behavior on small models (e.g. 3B lab runs).
        # Also keeps the ReAct loop legible step-by-step. Trade-off: more LLM round-trips
        # and higher token cost than batching multiple greets per turn.
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
