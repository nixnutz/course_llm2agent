"""Pure placeholder allowlist checks (finder + exact set membership)."""

import re

from src.logging_setup import get_logger

from .models import PlaceholderAllowlist, PlaceholderAuditResult

logger = get_logger(__name__, __file__)

# Placeholder-like tokens in LLM output (salt-agnostic finder; allowlist is the gate).
PLACEHOLDER_LIKE_RE = re.compile(r"E\d+_[0-9a-f]+")


def audit_placeholder_text(text: str, allowlist: PlaceholderAllowlist) -> PlaceholderAuditResult:
    """Return candidates and tokens that look like placeholders but are not allowed."""
    if not allowlist.allowed_tokens:
        return PlaceholderAuditResult(frozenset(), frozenset())

    allowed = frozenset(allowlist.allowed_tokens)
    candidates = frozenset(PLACEHOLDER_LIKE_RE.findall(text))
    unknown = candidates - allowed
    return PlaceholderAuditResult(candidates, unknown)


def audit_placeholder_texts(*texts: str, allowlist: PlaceholderAllowlist) -> PlaceholderAuditResult:
    """Audit one or more string fields as a single combined scan."""
    if not allowlist.allowed_tokens:
        return PlaceholderAuditResult(frozenset(), frozenset())

    allowed = frozenset(allowlist.allowed_tokens)
    candidates: set[str] = set()
    for text in texts:
        if text:
            candidates.update(PLACEHOLDER_LIKE_RE.findall(text))
    frozen_candidates = frozenset(candidates)
    return PlaceholderAuditResult(frozen_candidates, frozen_candidates - allowed)


def log_placeholder_violations(result: PlaceholderAuditResult, *, node: str) -> None:
    """Log each unknown token (Observe tier; see ADR 0012 — no state change today)."""
    for token in sorted(result.unknown_tokens):
        logger.warning("placeholder_violation node=%s token=%r", node, token)
