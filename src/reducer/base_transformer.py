"""Transform-hook reducer template — policy on messages entering graph state.

Course example of ``BaseReducer`` with **only** ``on_transform_message`` overridden.
``BaseReducer`` allows ``on_read_message`` and/or ``on_transform_message`` in one
subclass; ``BaseReducerReader`` covers observe-only (see ``base_reader``).

Use this template when the defense line should **change** what nodes see in
``state.messages`` (redaction, stripping fields, canonicalization). Nodes still
emit messages as usual; the reducer runs on every merge before the next node reads
the channel.

Hook (this class)
-----------------
* ``on_transform_message`` — demo logging; appends ``message.copy()`` to the
  per-thread vault before edits. The course demo replaces ``Hi`` with ``Moin`` on
  ``HumanMessage`` and appends the transformed copy again. Returns the message
  LangGraph should merge (prefer ``model_copy``, not in-place mutation).

Vault access (notebook)
-----------------------
Vaults live on the **reducer instance**, keyed by ``thread_id``. They are **not**
cleared when ``reducer_session`` exits (caller-owned lifecycle; see package
``__init__.py``).

Inside a session::

    with reducer_session("Chat-A", factory=make_transformer) as session:
        session.invoke(graph, session.state(MyState, [HumanMessage(...)]))
        vault = session.reducer.get_vault_for_thread(session.thread_id)
        for key, original in vault.get():
            ...

After the ``with``, the same vault is still reachable if you kept
``session.reducer`` (or a shared instance from a singleton factory). Drop data
with ``reducer.reset_for_thread("Chat-A")``.

Each ``reducer_session(..., factory=make_transformer)`` without sharing builds a
**new** transformer → separate vault storage. Reuse one instance (singleton
factory) to collect across notebook cells under different ``thread_id`` keys.

Wiring
------
Use ``reducer_session`` + ``session_message_reducer`` on the state class, with a
``factory`` that returns a **new** reducer per session (not a single instance
bound at notebook import time).

Example::

    def make_transformer(get_thread_id):
        return BaseReducerTransformer(get_thread_id=get_thread_id)

    class MyState(BaseModel):
        messages: Annotated[list[BaseMessage], session_message_reducer] = Field(...)

    with reducer_session("Chat-A", factory=make_transformer) as session:
        reply = session.invoke(
            graph, session.state(MyState, [HumanMessage(content="hello")])
        )
"""

from langchain_core.messages import BaseMessage, HumanMessage

from ..logging_setup import get_logger
from .base import BaseReducer

logger = get_logger(__name__, __file__)


class BaseReducerTransformer(BaseReducer):
    """Course template: ``on_transform_message`` only; vault before/after demo transform."""

    def on_transform_message(self, thread_id: str, message: BaseMessage) -> BaseMessage:
        if hasattr(message, "content") and isinstance(message.content, str):
            logger.debug(
                "transforming message content: %s",
                message.content,
                extra={"thread_id": thread_id},
            )

            vault = self.get_vault_for_thread(thread_id)
            key = str(message.id) if hasattr(message, "id") else ""
            vault.append(key, message.copy())

            if isinstance(message, HumanMessage) and "Hi" in message.content:
                # Don't do in-place modifications on the message object, create a new one instead
                new_content = message.content.replace("Hi", "Moin")
                message = message.model_copy(update={"content": new_content})
                logger.debug(
                    "replaced 'Hi' with 'Moin': %s",
                    message.content,
                    extra={"thread_id": thread_id},
                )
                vault.append(key, message.copy())

        else:
            logger.debug(
                "transforming message without content: %s",
                message,
                extra={"thread_id": thread_id},
            )
        return message
