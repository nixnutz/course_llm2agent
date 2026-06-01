"""Side storage outside graph state (for restore / audit flows).

Motivation
----------
If ``on_transform_message`` redacts or replaces message content in graph state,
callers may still need the original value later (audit, user reveal, rollback).
Storing secrets in graph state would expose them to every node; the vault keeps
data on the ``BaseReducer`` instance, outside LangGraph's ``messages`` channel.

One ``BaseVault`` exists per ``thread_id`` (conversation id). Obtain it via
``BaseReducer.get_vault_for_thread(thread_id)``. Entries persist until the
caller runs ``reset_for_thread(thread_id)`` — including across multiple
``reducer_session`` blocks when the same reducer instance is reused.

Storage model
-------------
Each vault is an **append-only chronological list** of ``(key, value)`` pairs.
There is no keyed lookup or overwrite: repeated ``append`` calls with the same
``key`` add another row. Course demos use ``str(message.id)`` as ``key`` and
``message.copy()`` as ``value`` (see ``BaseReducerReader`` / ``BaseReducerTransformer``).

Example (transform hook sketch)::

    vault = self.get_vault_for_thread(thread_id)
    vault.append(str(message.id), message.copy())
    redacted = message.model_copy(update={"content": redacted_content})
    return redacted

Inspect after a session (see ``langgraph_messages.ipynb``)::

    for key, original in vault.get():
        ...
"""

from typing import Any


class BaseVault:
    """Append-only (key, value) log for one conversation thread."""

    def __init__(self):
        self.store: list[tuple[str, Any]] = []

    def append(self, key: str, value: Any) -> None:
        """Record one entry; does not replace prior rows with the same ``key``."""
        self.store.append((key, value))

    def get(self) -> list[tuple[str, Any]]:
        """Return all entries in insertion order (same list as internal store)."""
        return self.store

    def clear(self) -> None:
        """Remove all entries (also invoked via ``BaseReducer.reset_for_thread``)."""
        self.store.clear()
