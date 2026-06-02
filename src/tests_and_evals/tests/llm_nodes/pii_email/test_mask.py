"""Deterministic unit tests for the email masking pipeline (``mask.py``).

These tests exercise the Python pipeline directly (no LLM): given the LLM
``occurrences`` they assert masked ``text``, placeholder/``identities`` mapping
and the soft-fail markers (span_not_found, normalization_failed).

Not exhaustive: course/WIP code. The non-deterministic part (which spans/raws
the LLM returns) is covered by the eval, not here.
"""

import re

import pytest

from src.llm_nodes.pii_email.mask import mask_pii_emails

_PLACEHOLDER_RE = re.compile(r"^E(\d+)_[0-9a-f]+$")


def _placeholders_in(text: str) -> list[str]:
    return re.findall(r"E\d+_[0-9a-f]+", text)


@pytest.mark.unit
def test_no_occurrences_keeps_text_unchanged():
    inp = "No contact info here."
    result = mask_pii_emails(inp, [])
    assert result.text == inp
    assert result.identities == []
    assert result.occurrences == []
    assert result.salt  # a salt is always generated


@pytest.mark.unit
def test_single_email_is_masked():
    inp = "Contact alice@example.com for details."
    result = mask_pii_emails(inp, [{"span": "alice@example.com", "raw": "alice@example.com"}])

    assert "alice@example.com" not in result.text
    assert result.identities == ["alice@example.com"]
    assert len(result.occurrences) == 1
    placeholder = result.occurrences[0].placeholder
    assert placeholder == f"E0_{result.salt}"
    assert result.text == f"Contact {placeholder} for details."


@pytest.mark.unit
def test_salt_not_present_in_input():
    inp = "Mail bob@example.com now."
    result = mask_pii_emails(inp, [{"span": "bob@example.com", "raw": "bob@example.com"}])
    assert result.salt not in inp


@pytest.mark.unit
def test_dedupe_same_canonical_shares_placeholder():
    # Two surface forms, same normalized address -> one identity, one placeholder.
    inp = "Ulf at phpdoc.de, ulf.wendel@phpdoc.de"
    occ = [
        {"span": "Ulf at phpdoc.de", "raw": "ulf.wendel@phpdoc.de"},
        {"span": "ulf.wendel@phpdoc.de", "raw": "ulf.wendel@phpdoc.de"},
    ]
    result = mask_pii_emails(inp, occ)

    assert result.identities == ["ulf.wendel@phpdoc.de"]
    placeholders = {o.placeholder for o in result.occurrences}
    assert placeholders == {f"E0_{result.salt}"}
    # Both spans replaced by the same token.
    assert result.text == f"E0_{result.salt}, E0_{result.salt}"


@pytest.mark.unit
def test_distinct_canonical_keys_get_separate_placeholders():
    inp = "a@x.com and b@y.com"
    occ = [
        {"span": "a@x.com", "raw": "a@x.com"},
        {"span": "b@y.com", "raw": "b@y.com"},
    ]
    result = mask_pii_emails(inp, occ)
    assert result.identities == ["a@x.com", "b@y.com"]
    assert result.text == f"E0_{result.salt} and E1_{result.salt}"


@pytest.mark.unit
def test_duplicate_identical_span_consumes_successive_occurrences():
    # Regression: identical span string appearing twice must mask BOTH places.
    inp = "mail a@x.com or a@x.com again"
    occ = [
        {"span": "a@x.com", "raw": "a@x.com"},
        {"span": "a@x.com", "raw": "a@x.com"},
    ]
    result = mask_pii_emails(inp, occ)

    assert "a@x.com" not in result.text
    token = f"E0_{result.salt}"
    assert result.text == f"mail {token} or {token} again"
    assert result.identities == ["a@x.com"]


@pytest.mark.unit
def test_canonical_key_is_strip_lower():
    inp = "Write to Foo@Bar.COM please"
    result = mask_pii_emails(inp, [{"span": "Foo@Bar.COM", "raw": "  Foo@Bar.COM  "}])
    assert result.identities == ["foo@bar.com"]
    assert result.occurrences[0].canonical_key == "foo@bar.com"


@pytest.mark.unit
def test_normalization_failed_masks_span_with_none_identity():
    # Span found in input but raw is not a valid email -> still masked, no restore.
    inp = "Reach broken add at nowhere today"
    result = mask_pii_emails(inp, [{"span": "broken add at nowhere", "raw": "not-an-email"}])

    assert "broken add at nowhere" not in result.text
    assert result.identities == [None]
    occ = result.occurrences[0]
    assert occ.canonical_key is None
    assert occ.placeholder == f"E0_{result.salt}"
    assert occ.skipped_reason is None  # masked, not skipped


@pytest.mark.unit
def test_span_not_found_is_skipped_and_raw_discarded():
    inp = "This text has no such span."
    result = mask_pii_emails(inp, [{"span": "ghost@nowhere.com", "raw": "ghost@nowhere.com"}])

    assert result.text == inp
    assert result.identities == []  # raw discarded, not added
    assert len(result.occurrences) == 1
    assert result.occurrences[0].skipped_reason == "span_not_found"
    assert result.occurrences[0].placeholder is None


@pytest.mark.unit
def test_placeholder_indices_follow_reading_order():
    # LLM returns occurrences out of reading order; indices must follow the text.
    inp = "first a@x.com then b@y.com"
    occ = [
        {"span": "b@y.com", "raw": "b@y.com"},
        {"span": "a@x.com", "raw": "a@x.com"},
    ]
    result = mask_pii_emails(inp, occ)
    # a@x.com appears first in the input -> E0, b@y.com -> E1.
    assert result.identities == ["a@x.com", "b@y.com"]
    assert result.text == f"first E0_{result.salt} then E1_{result.salt}"


@pytest.mark.unit
def test_restore_roundtrip_replaces_all_placeholders():
    inp = "Ping a@x.com, b@y.com and a@x.com"
    occ = [
        {"span": "a@x.com", "raw": "a@x.com"},
        {"span": "b@y.com", "raw": "b@y.com"},
        {"span": "a@x.com", "raw": "a@x.com"},
    ]
    result = mask_pii_emails(inp, occ)

    restored = result.text
    for index, email in enumerate(result.identities):
        if email is not None:
            restored = restored.replace(f"E{index}_{result.salt}", email)

    assert restored == inp
    assert not _placeholders_in(restored)


@pytest.mark.unit
def test_placeholder_format_is_indexed_and_salted():
    inp = "Hi a@x.com"
    result = mask_pii_emails(inp, [{"span": "a@x.com", "raw": "a@x.com"}])
    placeholders = _placeholders_in(result.text)
    assert placeholders, "expected a placeholder in the masked text"
    for token in placeholders:
        assert _PLACEHOLDER_RE.match(token)


@pytest.mark.unit
def test_non_dict_occurrences_are_ignored():
    inp = "Contact a@x.com"
    occ = ["garbage", None, {"span": "a@x.com", "raw": "a@x.com"}]
    result = mask_pii_emails(inp, occ)
    assert result.identities == ["a@x.com"]
    assert result.text == f"Contact E0_{result.salt}"
