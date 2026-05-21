"""Core reducer: LangGraph ``add_messages`` with optional read/transform hooks.

When nodes return ``{"messages": [new_msg, ...]}``, LangGraph calls the state's
message reducer as ``reducer(left, right)`` — no ``config``, no node reference.
This module implements that callable on ``BaseReducer``:

* **left** — messages already in graph state (processed once per ``thread_id``)
* **right** — new messages from the current step (processed every merge)

Hooks (override in subclasses)
------------------------------
``on_read_message(thread_id, message)``
    Observe only; use for logging, metrics, or policy checks.

``on_transform_message(thread_id, message) -> message``
    Return the message that should be merged (redaction, normalization, etc.).

The base class defines both hooks as ``NotImplementedError``. A hook runs only
when a **subclass** overrides it (``type(self).on_* is not BaseReducer.on_*``).
For this course, follow ``BaseReducerReader`` / ``BaseReducerTransformer``: plain
methods in the class body, no decorators or post-hoc assignment. That is enough
here; extend the detection only if a real use case appears.

After hooks, ``add_messages(left, right)`` performs the normal LangGraph merge.

Thread id
---------
Reducers receive ``get_thread_id: Callable[[], str]`` at construction time.
In practice that callable is ``reducer_session.get_thread_id``, which reads the
active session's conversation id (and aligns with ``ReducerSession.invoke``
config).

Vault
-----
``_vaults[thread_id]`` lazily creates a ``BaseVault`` per conversation id.
Hooks call ``_get_vault_for_thread`` to ``append`` originals outside graph state
(see ``base_reader`` / ``base_transformer``). Data survives across
``reducer_session`` blocks if the caller reuses the same ``BaseReducer`` and
``thread_id``. Call ``reset_for_thread(thread_id)`` when that conversation's
vault and left-scrub bookkeeping should be dropped (not automatic on session exit).

Example (subclass sketch)::

    class ScrubReducer(BaseReducer):
        def on_transform_message(self, thread_id, message):
            if isinstance(message.content, str):
                message.content = message.content.replace("PII", "REDACTED")
            return message
"""

from typing import Callable, cast

from langchain_core.messages import (
    BaseMessage,
    BaseMessageChunk,
    convert_to_messages,
    message_chunk_to_message,
)
from langgraph.graph.message import add_messages

from .base_vault import BaseVault


class BaseReducer:
    """LangGraph message reducer with optional per-message hooks.

    Subclasses override ``on_read_message`` and/or ``on_transform_message``.
    Unoverridden hooks are not invoked (base methods exist only as markers and
    raise if called directly on ``BaseReducer``).
    """

    def __init__(self, get_thread_id: Callable[[], str]):
        self._get_thread_id = get_thread_id
        self._left_scrubbed: dict[str, bool] = {}
        self._vaults: dict[str, BaseVault] = {}

    def _normalize_messages(self, messages) -> list[BaseMessage]:
        if not isinstance(messages, list):
            messages = [messages]
        return [
            message_chunk_to_message(cast(BaseMessageChunk, m))
            for m in convert_to_messages(messages)
        ]

    def __call__(self, left, right):
        """Merge message lists; hooks on ``right`` each time, on ``left`` once per thread."""
        thread_id = self._get_thread_id()
        on_read_callback = type(self).on_read_message is not BaseReducer.on_read_message
        on_transform_callback = (
            type(self).on_transform_message is not BaseReducer.on_transform_message
        )

        if on_read_callback or on_transform_callback:
            if not self._get_left_scrubbed_for_thread(thread_id):
                left = self._normalize_messages(left)
                if on_read_callback:
                    for m in left:
                        self.on_read_message(thread_id, m)
                if on_transform_callback:
                    left = [self.on_transform_message(thread_id, m) for m in left]
                self._set_left_scrubbed_for_thread(thread_id, True)

            right = self._normalize_messages(right)
            if on_read_callback:
                for m in right:
                    self.on_read_message(thread_id, m)
            if on_transform_callback:
                right = [self.on_transform_message(thread_id, m) for m in right]

        return add_messages(left, right)

    def _create_vault_for_thread(self, thread_id: str) -> BaseVault:
        if thread_id not in self._vaults:
            self._vaults[thread_id] = BaseVault()
        return self._vaults[thread_id]

    def clear_vault_for_thread(self, thread_id: str) -> None:
        if thread_id in self._vaults:
            self._vaults[thread_id].clear()
            del self._vaults[thread_id]

    def get_vault_for_thread(self, thread_id: str) -> BaseVault:
        return self._create_vault_for_thread(thread_id)

    def _get_left_scrubbed_for_thread(self, thread_id: str) -> bool:
        if thread_id not in self._left_scrubbed:
            self._left_scrubbed[thread_id] = False
        return self._left_scrubbed[thread_id]

    def _set_left_scrubbed_for_thread(self, thread_id: str, value: bool) -> None:
        self._left_scrubbed[thread_id] = value

    def reset_for_thread(self, thread_id: str):
        """Drop per-thread scrub/vault state; caller invokes when a conversation ends."""
        self._set_left_scrubbed_for_thread(thread_id, False)
        self.clear_vault_for_thread(thread_id)

    def reset_all(self) -> None:
        self._left_scrubbed.clear()
        self._vaults.clear()

    def on_read_message(self, thread_id: str, message: BaseMessage) -> None:
        raise NotImplementedError("on_read_message must be implemented in subclass")

    def on_transform_message(self, thread_id: str, message: BaseMessage) -> BaseMessage:
        raise NotImplementedError(
            "on_transform_message must be implemented in subclass"
        )
