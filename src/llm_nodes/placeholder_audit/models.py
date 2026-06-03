"""Minimal allowlist and audit result types (no raw email addresses)."""

from dataclasses import dataclass

from pydantic import Field

from ..base_state import BaseState


class PlaceholderAllowlist(BaseState):
    """Session placeholder tokens for audit only — no raw email addresses."""

    allowed_tokens: tuple[str, ...] = Field(default_factory=tuple)


@dataclass(frozen=True)
class PlaceholderAuditResult:
    """Outcome of scanning text for placeholder-like tokens against an allowlist."""

    candidates: frozenset[str]
    unknown_tokens: frozenset[str]
