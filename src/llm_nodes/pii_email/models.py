"""Structured output for the PII email extraction node.

The LLM only reports detected email spans plus a normalized address per span
(see ``prompts.py``). The masked ``text``, placeholder assignment and
deduplication are produced deterministically in Python (see ``mask.py``).
"""

from pydantic import Field

from ..base_state import BaseState


class Occurrence(BaseState):
    """One detected email span and how the pipeline handled it.

    ``placeholder`` / ``email`` are ``None`` when the span was not
    located in the input or could not be normalized.

    - ``span``: verbatim substring as it appeared in the input.
    - ``raw_llm``: raw address string as reported by the LLM (internal detail).
    - ``email``: mail-ready address derived from ``raw_llm``; ``None`` if not
      normalizable.
    """

    span: str = Field(default="")
    raw_llm: str = Field(default="")
    email: str | None = None
    placeholder: str | None = None
    skipped_reason: str | None = None


class PIIEmail(BaseState):
    """Masked text with ``E{n}_{salt}`` placeholders plus recovery metadata.

    - ``emails[n]`` is the mail-ready address behind placeholder ``E{n}_{salt}``;
      ``None`` means the span was masked but could not be normalized (no restore).
    - ``occurrences`` keeps the per-span audit trail for logging/debugging.
    """

    text: str = Field(default="")
    salt: str = Field(default="")
    emails: list[str | None] = Field(default_factory=list)
    occurrences: list[Occurrence] = Field(default_factory=list)
