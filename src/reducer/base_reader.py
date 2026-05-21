"""Observe-only reducer: read messages between nodes without changing content.

Use this variant when the defense line should **monitor** inter-node traffic
(log, count, alert) but leave message payloads unchanged in graph state.
The course demo also appends ``message.copy()`` into the per-thread ``BaseVault``.

Prefer wiring graphs through ``reducer_session.session_message_reducer`` and a
``factory`` that returns ``BaseReducerReader`` — not a long-lived
``build_reducer_reader()`` instance at notebook import time.

Example::

    def make_reader(get_thread_id):
        return BaseReducerReader(get_thread_id=get_thread_id)

    with reducer_session("audit-1", factory=make_reader) as session:
        state = session.state(MyState, [HumanMessage(content="...")])
        session.invoke(graph, state)
"""

from typing import Callable

from langchain_core.messages import BaseMessage

from .base import BaseReducer


class BaseReducerReader(BaseReducer):
    """Observe-only reducer: overrides ``on_read_message`` only (stdout demo)."""

    def on_read_message(self, thread_id: str, message: BaseMessage) -> None:
        if hasattr(message, "content") and isinstance(message.content, str):
            print(
                f"REDUCER (thread={thread_id}): observing message content: {message.content}"
            )
            vault = self.get_vault_for_thread(thread_id)
            if hasattr(message, "id"):
                key = str(message.id)
            else:
                key = ""
            vault.append(key, message.copy())
        else:
            print(
                f"REDUCER (thread={thread_id}): observing message without content: {message}"
            )


def build_reducer_reader(get_thread_id: Callable[[], str]):
    """Return a LangGraph ``message_reducer(left, right)`` closure (legacy helper).

    Binds one ``BaseReducerReader`` at build time. For session-scoped instances,
    use ``reducer_session(..., factory=make_reader)`` and
    ``session_message_reducer`` on the state class instead.
    """
    reader = BaseReducerReader(get_thread_id=get_thread_id)

    def message_reducer(left, right):
        return reader(left, right)

    return message_reducer
