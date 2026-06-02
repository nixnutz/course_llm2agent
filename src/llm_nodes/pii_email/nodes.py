"""LangGraph node: mask emails in the latest human message, update ``pii_email``."""

from langchain_core.messages import AIMessage, convert_to_openai_messages
from langchain_core.prompts import ChatPromptTemplate

from ...llm_handle.local import (
    AsyncClientProvider,
    ClientCachePolicy,
    make_async_openai_client_provider,
)
from ..global_state import GlobalState
from ..parse_llm_json import ParseLLMJson
from .mask import mask_pii_emails
from .prompts import _pii_email_prompt


class LlmNodePIIExtract:
    """Async callable; appends AI JSON trace and merges ``pii_email`` into state."""

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

    async def __call__(self, state: GlobalState) -> dict:
        last_human = next(
            (m for m in reversed(state.messages) if m.type == "human"),
            None,
        )
        if last_human is None or not isinstance(last_human.content, str):
            raise ValueError("Expected at least one human message with string content")

        prompt_value = self._template.invoke({"input": last_human.content})
        openai_messages = convert_to_openai_messages(prompt_value.messages)
        completion = await self._client.chat.completions.create(
            model=self._model,
            messages=openai_messages,
            temperature=0.0,
        )
        answer = completion.choices[0].message.content or ""
        raw = ParseLLMJson().parse_as_dict(answer)
        occurrences = raw.get("occurrences", [])
        if not isinstance(occurrences, list):
            raise ValueError("LLM JSON field 'occurrences' must be a list")

        parsed = mask_pii_emails(last_human.content, occurrences)

        return {
            "messages": [AIMessage(content=answer.strip())],
            "pii_email": parsed,
        }


def get_pii_email_node(
    model: str,
    client_provider: AsyncClientProvider | None = None,
    client_cache_policy: ClientCachePolicy = "cached",
):
    return LlmNodePIIExtract(
        model=model,
        template=_pii_email_prompt,
        client_provider=client_provider,
        client_cache_policy=client_cache_policy,
    )
