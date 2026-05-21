"""Observe-only reducer: read messages between nodes without changing content.

Use this variant when the defense line should **monitor** inter-node traffic
(log, count, alert) but leave message payloads unchanged in graph state.
The course demo also appends ``message.copy()`` into the per-thread ``BaseVault``.

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
