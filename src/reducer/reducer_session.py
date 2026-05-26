"""Session scope for reducers: thread id, active instance, state/invoke helpers.

Problem
-------
LangGraph calls ``message_reducer(left, right)`` with no session metadata. The
reducer still needs:

* a **conversation id** (``thread_id``) for per-chat vaults and scrub flags
* a **concrete reducer instance** per ``with`` block (not one global object for
  the whole notebook)

This module supplies both via ``contextvars``, set for the duration of
``reducer_session(...)``.

Typical notebook flow
---------------------
::

    from src.reducer.reducer_session import reducer_session, session_message_reducer
    from src.reducer.base_transformer import BaseReducerTransformer

    def make_transformer(get_thread_id):
        return BaseReducerTransformer(get_thread_id=get_thread_id)

    class MyState(BaseModel):
        messages: Annotated[list[BaseMessage], session_message_reducer] = Field(...)

    with reducer_session("Chat-A", factory=make_transformer) as session:
        state = session.state(MyState, [HumanMessage(content="hello")])
        reply = await session.ainvoke(graph, state)

``invoke`` / ``ainvoke`` and ``config``
---------------------------------------
* ``config=None`` → uses ``{"configurable": {"thread_id": session.thread_id}}``.
* ``config`` with ``configurable.thread_id`` → must equal the session's id, or
  ``RuntimeError``.
* Returned config is always merged so ``configurable.thread_id`` is the session's
  (LangGraph tracing/checkpointing stays aligned with reducer vault keys).

Guards
------
* ``_require_active_session()`` — context set and same OS thread as session open.
* ``_require_this_session(session)`` — the yielded handle is the active session
  and ``current_reducer`` matches ``session.reducer`` (for ``state`` / ``invoke`` / ``ainvoke``).
* ``get_thread_id()`` / ``get_active_reducer()`` / ``session_message_reducer`` use
  the active session.

One ``with`` block uses **one** reducer instance (chosen by ``factory`` at entry).
A different policy requires another ``with`` or a different ``factory``.

Lifetime
--------
Exiting ``reducer_session`` does **not** clear vaults or ``_left_scrubbed`` on the
reducer — only the active session context. Reuse one reducer across several
``with`` blocks to keep vault data; call ``reducer.reset_for_thread(thread_id)``
when the caller is done with that conversation.

Threading
---------
Reducer session is bound to the OS thread that entered ``reducer_session``.
Calls from another thread fail fast (no silent context loss).
"""

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
import threading
from typing import Callable, TypeVar
from uuid import uuid4

from langchain_core.messages import BaseMessage

from .base import BaseReducer

T = TypeVar("T")

_current_reducer: ContextVar[BaseReducer | None] = ContextVar("current_reducer", default=None)
_session_var: ContextVar["ReducerSession | None"] = ContextVar("reducer_session", default=None)

ReducerFactory = Callable[[Callable[[], str]], BaseReducer]


@dataclass(frozen=True)
class ReducerSession:
    """Handle yielded by ``reducer_session``; use for ``state``, ``invoke``, or ``ainvoke``."""

    thread_id: str
    owner_thread_ident: int
    reducer: BaseReducer

    @property
    def config(self) -> dict:
        """Default LangGraph config for this conversation."""
        return {"configurable": {"thread_id": self.thread_id}}

    def state(self, state_cls: type[T], messages: list[BaseMessage]) -> T:
        """Build graph input state only while this session is active."""
        _require_this_session(self)
        return state_cls(messages=messages)

    def invoke(self, graph, input_state, config: dict | None = None):
        """Run ``graph.invoke`` with session-checked config."""
        _require_this_session(self)
        safe_config = _assert_config_matches_session(self, config)
        return graph.invoke(input_state, config=safe_config)

    async def ainvoke(self, graph, input_state, config: dict | None = None):
        """Run ``graph.ainvoke`` with session-checked config."""
        _require_this_session(self)
        safe_config = _assert_config_matches_session(self, config)
        return await graph.ainvoke(input_state, config=safe_config)

    def _check_owner_thread(self) -> None:
        if threading.get_ident() != self.owner_thread_ident:
            raise RuntimeError(
                f"Reducer session is bound to a different OS thread. "
                f"owner={self.owner_thread_ident}, current={threading.get_ident()}, "
                f"thread_id={self.thread_id}. "
                "Threaded execution is not supported."
            )


def _assert_config_matches_session(
    session: ReducerSession,
    config: dict | None,
) -> dict:
    """Ensure LangGraph config ``thread_id`` matches the active session."""
    if config is None:
        return session.config

    configurable = config.get("configurable") or {}
    other_thread_id = configurable.get("thread_id")
    if other_thread_id is not None and other_thread_id != session.thread_id:
        raise RuntimeError(
            f"Config thread_id {other_thread_id!r} does not match session "
            f"thread_id {session.thread_id!r}. "
            "Use session.invoke()/ainvoke() without a conflicting thread_id."
        )

    merged_config = dict(config)
    if not isinstance(merged_config.get("configurable"), dict):
        merged_config["configurable"] = {}
    merged_config["configurable"]["thread_id"] = session.thread_id
    return merged_config


def _require_active_session() -> ReducerSession:
    session = _session_var.get()
    if session is None:
        raise RuntimeError(
            "Reducer session is not set. "
            "Use reducer_session(...) and run graph.invoke()/ainvoke()/stream() "
            "inside that with block (prefer session.invoke/ainvoke for config)."
        )
    session._check_owner_thread()
    return session


def _require_this_session(session: ReducerSession) -> ReducerSession:
    active = _require_active_session()
    if active is not session:
        raise RuntimeError(
            "This ReducerSession is not the active session. "
            "Use the object yielded by reducer_session(...) in the same with block."
        )
    if _current_reducer.get() is not session.reducer:
        raise RuntimeError(
            "No active reducer in context. "
            "Use reducer_session(..., factory=...) before running the graph."
        )
    return active


def get_thread_id() -> str:
    """Conversation id for the active ``reducer_session`` block."""
    return _require_active_session().thread_id


def get_active_reducer() -> BaseReducer:
    """Reducer instance for the active ``reducer_session`` block."""
    session = _require_active_session()
    reducer = _current_reducer.get()
    if reducer is None or reducer is not session.reducer:
        raise RuntimeError(
            "No active reducer in context. "
            "Use reducer_session(..., factory=...) before running the graph."
        )
    return reducer


def session_message_reducer(left, right):
    """LangGraph entry point; delegates to the active session's reducer."""
    return get_active_reducer()(left, right)


def get_session() -> ReducerSession:
    return _require_active_session()


def set_session(thread_id: str, reducer: BaseReducer) -> tuple[Token, Token]:
    session = ReducerSession(
        thread_id=thread_id,
        owner_thread_ident=threading.get_ident(),
        reducer=reducer,
    )
    return _session_var.set(session), _current_reducer.set(reducer)


def reset_session(token_session: Token, token_reducer: Token) -> None:
    _session_var.reset(token_session)
    _current_reducer.reset(token_reducer)


@contextmanager
def reducer_session(thread_id: str | None = None, *, factory: ReducerFactory):
    """Open a session; yield a ``ReducerSession`` handle.

    ``factory`` receives ``get_thread_id`` and returns a ``BaseReducer`` instance.
    Does not call ``reset_for_thread`` on exit — vault lifetime is caller-owned.
    """
    thread_id = thread_id or str(uuid4())
    reducer = factory(get_thread_id)
    token_session, token_reducer = set_session(thread_id, reducer)
    try:
        yield get_session()
    finally:
        reset_session(token_session, token_reducer)
