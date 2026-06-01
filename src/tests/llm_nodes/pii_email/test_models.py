"""Tests for ``PIIEmail`` (minimal coverage).

Summary:
- Default empty lists and ``extra="forbid"`` on ``BaseState``.
- Field transformers: ``raw_emails`` (strip + lower), ``recognized_emails`` (strip only).
- Model validator: derives ``normalized_emails`` from ``raw_emails`` (invalid → ``None``).
- Length parity between ``recognized_emails`` and ``raw_emails``.

Not exhaustive: this node is course/WIP code, not production, and ``models.py`` may still
change.
"""

from pydantic import ValidationError
import pytest

from src.llm_nodes.pii_email.models import PIIEmail


def test_minimal_defaults():
    result = PIIEmail(text="No emails here.")
    assert result.text == "No emails here."
    assert result.recognized_emails == []
    assert result.raw_emails == []
    assert result.normalized_emails == []


def test_valid_consistent_lists():
    result = PIIEmail(
        text="This is a confidential email: Test@example.com, Test2@example.com",
        recognized_emails=["Test@example.com", "Test2@example.com"],
        raw_emails=["test@example.com", "test2@example.com"],
    )
    assert result.recognized_emails == ["Test@example.com", "Test2@example.com"]
    assert result.raw_emails == ["test@example.com", "test2@example.com"]
    assert str(result.normalized_emails[0]) == "test@example.com"
    assert str(result.normalized_emails[1]) == "test2@example.com"


def test_auto_normalization_mixed_valid_invalid():
    result = PIIEmail(
        text="Contact: good@example.com or bad address",
        recognized_emails=["good@example.com", "not-an-email"],
        raw_emails=["good@example.com", "not-an-email"],
    )
    assert str(result.normalized_emails[0]) == "good@example.com"
    assert result.normalized_emails[1] is None


def test_raw_emails_strip_and_lower():
    result = PIIEmail(
        text="x",
        recognized_emails=["x@y.com"],
        raw_emails=["  Foo@Bar.COM  "],
    )
    assert result.raw_emails == ["foo@bar.com"]


def test_recognized_emails_strip_preserves_case():
    result = PIIEmail(
        text="x",
        recognized_emails=["  Test@Example.COM  "],
        raw_emails=["test@example.com"],
    )
    assert result.recognized_emails == ["Test@Example.COM"]


def test_invalid_email_same_lengths_normalized_none():
    result = PIIEmail(
        text="This is a confidential email",
        recognized_emails=["test at example.com"],
        raw_emails=["test at example.com"],
    )
    assert result.normalized_emails == [None]


def test_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        PIIEmail(text="x", unknown_field=1)


def test_length_mismatch_recognized_vs_raw():
    with pytest.raises(ValidationError) as exc_info:
        PIIEmail(
            text="Email thread",
            recognized_emails=[
                "test@example.com",
                "test2@example.com",
                "test3@example.com",
            ],
            raw_emails=["test@example.com", "test2@example.com"],
        )
    assert "recognized_emails and raw_emails must have the same length" in str(exc_info.value)


def test_length_mismatch_recognized_shorter_than_raw():
    with pytest.raises(ValidationError) as exc_info:
        PIIEmail(
            text="This is a confidential email",
            recognized_emails=["test at example.com"],
            raw_emails=["test at example.com", "test2@example.com"],
        )
    msg = str(exc_info.value)
    assert "recognized_emails and raw_emails must have the same length" in msg
