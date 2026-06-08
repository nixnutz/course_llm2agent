"""LangGraph nodes for the tool_node_loop subgraph (agent + LangGraph ToolNode).

TODO (deferred decisions — course WIP, no ADR yet)
-------------------------------------------------
1. **LLM client layering (A vs B)** — ``ToolNodeLoopAgent`` builds ``ChatOpenAI``
   while ``llm_handle.local`` caches ``openai.AsyncOpenAI``. We only reuse
   ``base_url`` / ``api_key`` from the provider today; the AsyncOpenAI cache entry
   is bypassed. Pick one target later:
   - **A:** tool agent like ``todo_markdown`` — ``AsyncOpenAI`` + manual ``tools=``
     and ``AIMessage(tool_calls=...)`` assembly.
   - **B:** extend ``local.py`` with a cached ``ChatOpenAI`` (+ ``bind_tools``) factory
     so nodes stay on the provider pattern without re-reading config.
   Decision deferred until a real tool executor and loop policy are clearer.

2. **Tool surface** — ``greet`` in ``tools.py`` is a symbolic ``@tool`` demo. A later
   ``tool_custom_loop`` package may swap ToolNode for a custom executor without
   changing this reference loop.

3. **Tool-loop exit policy** — ``route_after_agent`` covers max rounds/errors plus
   ``tool_calls``; not yet: wall-clock budget, human-in-the-loop, per-tool caps.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode

from src.errors import PipelinePreconditionError

from ...llm_handle.local import (
    AsyncClientProvider,
    ClientCachePolicy,
    create_httpx_async_client,
    make_async_openai_client_provider,
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
        client_provider: AsyncClientProvider | None = None,
        client_cache_policy: ClientCachePolicy = "cached",
    ):
        provider = client_provider or make_async_openai_client_provider(
            client_cache_policy=client_cache_policy
        )
        openai_client = provider()
        # TODO: see module docstring — AsyncOpenAI cache vs ChatOpenAI (A/B deferred).
        llm = ChatOpenAI(
            model=model,
            base_url=str(openai_client.base_url),
            api_key=openai_client.api_key,
            temperature=0.0,
            http_async_client=create_httpx_async_client(),
        )
        self._llm = llm.bind_tools(TOOLS, parallel_tool_calls=False)
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
    client_provider: AsyncClientProvider | None = None,
    client_cache_policy: ClientCachePolicy = "cached",
):
    return ToolNodeLoopAgent(
        model=model,
        template=_tool_node_loop_prompt,
        client_provider=client_provider,
        client_cache_policy=client_cache_policy,
    )


# Tool execution (LangGraph prebuilt ToolNode).
# handle_tool_errors=True  → Observe (ADR 0012): error text in ToolMessage, loop continues.
# handle_tool_errors=False → Fail-fast: exception aborts the subgraph run.
HANDLE_TOOL_ERRORS = True
_TOOL_NODE = ToolNode(TOOLS, handle_tool_errors=HANDLE_TOOL_ERRORS)


def get_tool_node_loop_tool_node() -> ToolNode:
    return _TOOL_NODE
