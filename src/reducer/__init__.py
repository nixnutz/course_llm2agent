"""Message reducers for LangGraph — a defense line outside graph nodes.

Motivation
----------
Nodes in a LangGraph graph communicate by appending to a shared ``messages`` channel.
That channel is a natural place to enforce policy: every message that enters or
accumulates in graph state passes through the reducer LangGraph attaches to that
field. Hooks run *outside* individual nodes, so a node cannot simply opt out of
the reducer the way it might skip an internal helper.

This package is course infrastructure, not a complete security product. The goal
is to **observe** traffic between nodes (``on_read_message``) and optionally
**transform** what ends up in state (``on_transform_message``) — for example
redacting sensitive substrings before the next node runs. A ``BaseVault`` per
``thread_id`` on the reducer keeps message copies outside graph state (course
demos append in read/transform hooks).

What happens between nodes
--------------------------
Each node returns partial state updates (typically ``{"messages": [new_msg]}``).
LangGraph merges them into the shared ``messages`` list via the reducer:

1. **``right``** — new messages from the current step: hooks run on every merge.
2. **``add_messages``** — LangGraph's normal append/merge rules apply.
3. **Next node** reads ``state.messages`` — already whatever ``on_transform_message``
   returned (redacted, logged, or unchanged).

On the **first** ``invoke`` of a conversation, existing messages in the input state
are passed as **``left``**; hooks run on ``left`` once per ``thread_id`` (see
``BaseReducer._left_scrubbed`` in ``base.py``).

Limitations (non-goals)
-----------------------
* **Only guarded channels** — policy applies to state fields wired with
  ``session_message_reducer`` (or another ``BaseReducer`` callable). Other fields
  (``steps``, tool payloads, custom dicts) are unaffected.
* **No coverage of side-channel I/O** — a node can still call an LLM or HTTP API
  directly; that traffic never passes through this reducer.
* **Same trust domain** — reducer code runs in the same process as the graph.
  This is contract enforcement for course experiments, not isolation from malicious
  node code.
* **Session context is manual** — ``reducer_session`` must wrap each ``invoke`` /
  ``stream`` (and similar). Checkpoint resume does not restore ContextVars; reopen
  the session before continuing.
* **Not a full security product** — no guarantee against prompt injection, tool
  abuse, or state fields that bypass ``messages``.

Out of scope (for now)
----------------------
* Real PII redaction or policy-driven transforms (demos log and vault copies only)
* Keyed vault lookup / deduplication by message id (append-only list today)
* ``stream()`` wrapper on ``ReducerSession``
* Strict matching of State class vs ``factory`` reducer type (convention only)
* Async / threaded execution with context propagation

Architecture (high level)
-----------------------
::

    with reducer_session("Chat-A", factory=make_transformer) as session:
        state = session.state(MyState, messages=[HumanMessage(...)])
        reply = session.invoke(graph, state)   # config thread_id = "Chat-A"

    # LangGraph merges message updates via session_message_reducer(left, right)
    #   -> get_active_reducer()  (ContextVar set by reducer_session)
    #   -> BaseReducer.__call__  (hooks, then add_messages)

Session safety (``reducer_session``)
------------------------------------
* ``state()`` / ``invoke()`` only work on the **yielded** ``ReducerSession`` while
  its ``with`` block is active.
* ``invoke(..., config=...)`` may omit ``config`` (session default is used) or pass
  a dict whose ``configurable.thread_id`` must match the session; the session
  always injects its ``thread_id`` into the merged config.

Reducer / vault lifetime (caller-owned)
---------------------------------------
* Leaving ``reducer_session`` clears **ContextVars only** — not ``_left_scrubbed``,
  vaults, or other state on the ``BaseReducer`` instance.
* The same reducer instance may serve **multiple** ``with`` blocks (e.g. one vault
  across sessions for the same ``thread_id``). The **caller** decides when to drop
  per-thread data via ``reset_for_thread(thread_id)``.

Modules
-------
``reducer_session``
    Session scope: ``thread_id``, active reducer instance, ``state()``, ``invoke()``.
``base``
    ``BaseReducer``: hook orchestration and per-``thread_id`` bookkeeping/vaults.
``base_reader`` / ``base_transformer``
    Course templates: observe-only (``on_read_message``) vs transform-only
    (``on_transform_message``). A single ``BaseReducer`` subclass may implement
    either hook or both; the split keeps notebooks focused.
``base_vault``
    Per-thread append-only ``(key, value)`` log outside graph ``messages``.

See ``src/assorted/session3/langgraph_message.ipynb`` for a minimal mock graph."""
