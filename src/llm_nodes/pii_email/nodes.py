"""LangGraph node: mask emails in the latest human message, update ``pii_email``."""

from langchain_core.messages import AIMessage, convert_to_openai_messages
from langchain_core.prompts import ChatPromptTemplate

from ...llm_handle.local import get_async_openai_client
from ..global_state import GlobalState
from ..parse_llm_json import parse_llm_json
from .models import PIIEmail
from .prompts import _pii_email_prompt


class LlmNodePIIExtract:
    """Async callable; appends AI JSON trace and merges ``pii_email`` into state."""

    def __init__(self, model: str, template: ChatPromptTemplate):
        self._client = get_async_openai_client()
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
        parsed = parse_llm_json(answer, PIIEmail)

        return {
            "messages": [AIMessage(content=answer.strip())],
            "pii_email": parsed,
        }


def get_pii_email_node(model: str):
    return LlmNodePIIExtract(model=model, template=_pii_email_prompt)
