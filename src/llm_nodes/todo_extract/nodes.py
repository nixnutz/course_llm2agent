"""LangGraph node: extract TODO rows from ``pii_email.text``, update ``todo_list``."""

from langchain_core.messages import AIMessage, convert_to_openai_messages
from langchain_core.prompts import ChatPromptTemplate

from src.errors import PipelinePreconditionError

from ...llm_handle.local import (
    AsyncClientProvider,
    ClientCachePolicy,
    make_async_openai_client_provider,
)
from ..parse_llm_json import ParseLLMJson
from .models import TODOList, TODOState
from .prompts import _todo_list_prompt


class LlmNodeTODOList:
    """Async callable; reads redacted text, appends AI JSON trace and ``todo_list``."""

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

    async def __call__(self, state: TODOState) -> dict:
        if not state.text:
            raise PipelinePreconditionError("Expected non-empty text")

        input_text = state.text

        prompt_value = self._template.invoke({"input": input_text})
        openai_messages = convert_to_openai_messages(prompt_value.messages)
        completion = await self._client.chat.completions.create(
            model=self._model,
            messages=openai_messages,
            temperature=0.0,
        )
        answer = completion.choices[0].message.content or ""
        parsed = ParseLLMJson().parse_as_model(answer, TODOList)

        return {
            "messages": [AIMessage(content=answer.strip())],
            "todo_list": parsed,
        }


def get_todo_list_node(
    model: str,
    client_provider: AsyncClientProvider | None = None,
    client_cache_policy: ClientCachePolicy = "cached",
):
    return LlmNodeTODOList(
        model=model,
        template=_todo_list_prompt,
        client_provider=client_provider,
        client_cache_policy=client_cache_policy,
    )
