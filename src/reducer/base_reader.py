"""Observe-only reducer: read messages between nodes without changing content.

Use this variant when the defense line should **monitor** inter-node traffic
(log, count, alert) but leave message payloads unchanged in graph state.
The course demo also appends ``message.model_copy()`` into the per-thread ``BaseVault``.

Wire graphs through ``reducer_session``, ``session_message_reducer``, and a
``factory`` that returns a **new** ``BaseReducerReader`` per session (not a
reducer instance created at notebook import time).

Example::

    def make_reader(get_thread_id):
        return BaseReducerReader(get_thread_id=get_thread_id)

    with reducer_session("audit-1", factory=make_reader) as session:
        state = session.state(MyState, [HumanMessage(content="...")])
        session.invoke(graph, state)
"""

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from ..logging_setup import get_logger
from .base import BaseReducer

logger = get_logger(__name__, __file__)


class BaseReducerReader(BaseReducer):
    """Observe-only reducer: overrides ``on_read_message`` only (stdout demo)."""

    def _vault_message(self, thread_id: str, message: BaseMessage) -> None:
        vault = self.get_vault_for_thread(thread_id)
        key = str(message.id) if hasattr(message, "id") else ""
        vault.append(key, message.model_copy())

    def on_read_message(self, thread_id: str, message: BaseMessage) -> None:
        extra = {"thread_id": thread_id}

        if isinstance(message, AIMessage) and message.tool_calls:
            logger.debug("observing tool_calls: %s", message.tool_calls, extra=extra)
        elif isinstance(message, ToolMessage):
            logger.debug(
                "observing tool result [%s] (id=%s): %s",
                message.name,
                message.tool_call_id,
                message.content,
                extra=extra,
            )
        elif hasattr(message, "content") and isinstance(message.content, str):
            logger.debug("observing message content: %s", message.content, extra=extra)
        else:
            logger.debug("observing message without content: %s", message, extra=extra)

        self._vault_message(thread_id, message)
