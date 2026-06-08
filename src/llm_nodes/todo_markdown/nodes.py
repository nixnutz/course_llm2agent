"""LangGraph node: render TODO list payload into markdown."""

from langchain_core.messages import AIMessage, convert_to_openai_messages
from langchain_core.prompts import ChatPromptTemplate

from src.errors import PipelinePreconditionError

from ...llm_handle.local import (
    AsyncClientProvider,
    ClientCachePolicy,
    make_async_openai_client_provider,
)
from .models import TODOMarkdown, TODOMarkdownState
from .prompts import _todo_markdown_prompt


class LlmNodeTODOMarkdown:
    """Async callable; reads TODO payload and returns markdown schema."""

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
        self._client = provider()
        self._model = model
        self._template = template

    async def __call__(self, state: TODOMarkdownState) -> dict:
        if not state.todo_list_json:
            raise PipelinePreconditionError("Expected non-empty todo_list_json")

        prompt_value = self._template.invoke({"input": state.todo_list_json})
        openai_messages = convert_to_openai_messages(prompt_value.messages)
        completion = await self._client.chat.completions.create(
            model=self._model,
            messages=openai_messages,
            temperature=0.0,
        )
        answer = (completion.choices[0].message.content or "").strip()
        parsed = TODOMarkdown(markdown=answer)
        return {
            "messages": [AIMessage(content=answer)],
            "todo_markdown": parsed,
        }


def get_todo_markdown_node(
    model: str,
    client_provider: AsyncClientProvider | None = None,
    client_cache_policy: ClientCachePolicy = "cached",
):
    return LlmNodeTODOMarkdown(
        model=model,
        template=_todo_markdown_prompt,
        client_provider=client_provider,
        client_cache_policy=client_cache_policy,
    )
