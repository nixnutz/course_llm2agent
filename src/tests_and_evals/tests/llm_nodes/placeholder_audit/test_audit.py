"""Unit tests for placeholder allowlist audit (no LLM)."""

import pytest

from src.llm_nodes.placeholder_audit import (
    PlaceholderAllowlist,
    allowlist_from_pii_email,
    audit_placeholder_text,
)
from src.llm_nodes.pii_email.models import PIIEmail

_SALT = "a1b2c3d4"


def _allowlist(*indices: int) -> PlaceholderAllowlist:
    return PlaceholderAllowlist(
        allowed_tokens=tuple(f"E{i}_{_SALT}" for i in indices)
    )


@pytest.mark.unit
def test_allowed_token_passes():
    allowlist = _allowlist(0)
    token = allowlist.allowed_tokens[0]
    result = audit_placeholder_text(f"Task {token} today.", allowlist)
    assert not result.unknown_tokens


@pytest.mark.unit
def test_invented_index_reported():
    allowlist = _allowlist(0, 1)
    token = f"E99_{_SALT}"
    result = audit_placeholder_text(f"who {token}", allowlist)
    assert token in result.unknown_tokens


@pytest.mark.unit
def test_wrong_salt_token_reported():
    allowlist = _allowlist(0)
    foreign = "E0_cafebabe"
    result = audit_placeholder_text(f"who {foreign}", allowlist)
    assert foreign in result.unknown_tokens


@pytest.mark.unit
def test_truncated_but_placeholder_like_is_reported():
    """Short hex suffix still matches E{n}_{hex} and fails exact allowlist match."""
    allowlist = _allowlist(0)
    truncated = f"E0_{_SALT[:6]}"
    result = audit_placeholder_text(f"who {truncated}", allowlist)
    assert truncated in result.unknown_tokens


@pytest.mark.unit
def test_malformed_separator_not_reported():
    """Limitation: token must match E{digits}_{hex}; wrong separator is invisible to audit."""
    allowlist = _allowlist(0)
    malformed = f"E0-{_SALT}"
    result = audit_placeholder_text(f"who {malformed}", allowlist)
    assert malformed not in result.candidates
    assert not result.unknown_tokens


@pytest.mark.unit
def test_unknown_who_not_reported():
    allowlist = _allowlist(0)
    result = audit_placeholder_text('who UNKNOWN what x when y', allowlist)
    assert not result.unknown_tokens


@pytest.mark.unit
def test_empty_allowlist_is_noop():
    result = audit_placeholder_text(f"E0_{_SALT}", PlaceholderAllowlist())
    assert not result.candidates
    assert not result.unknown_tokens


@pytest.mark.unit
def test_allowlist_from_pii_email_uses_count_not_addresses():
    pii = PIIEmail(
        text="x",
        salt=_SALT,
        emails=["a@b.com", "c@d.com"],
    )
    allowlist = allowlist_from_pii_email(pii)
    assert allowlist.allowed_tokens == (f"E0_{_SALT}", f"E1_{_SALT}")
    assert "a@b.com" not in str(allowlist.allowed_tokens)
