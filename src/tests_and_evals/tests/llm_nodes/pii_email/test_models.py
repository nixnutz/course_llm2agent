"""Tests for ``PIIEmail`` / ``Occurrence`` (minimal coverage).

Summary:
- Default empty values and ``extra="forbid"`` on ``BaseState``.
- ``emails`` may hold ``None`` (recognized but not normalizable).
- ``Occurrence`` defaults.

Not exhaustive: course/WIP code. Masking behavior is covered in ``test_mask.py``.
"""

from pydantic import ValidationError
import pytest

from src.llm_nodes.pii_email.models import Occurrence, PIIEmail


@pytest.mark.unit
def test_minimal_defaults():
    result = PIIEmail()
    assert result.text == ""
    assert result.salt == ""
    assert result.emails == []
    assert result.occurrences == []


@pytest.mark.unit
def test_emails_allow_none():
    result = PIIEmail(text="x", salt="abcd", emails=["a@b.com", None])
    assert result.emails == ["a@b.com", None]


@pytest.mark.unit
def test_occurrence_defaults():
    occ = Occurrence(span="a@b.com", raw_llm="a@b.com")
    assert occ.span == "a@b.com"
    assert occ.raw_llm == "a@b.com"
    assert occ.email is None
    assert occ.placeholder is None
    assert occ.skipped_reason is None


@pytest.mark.unit
def test_occurrences_accept_nested_models():
    result = PIIEmail(
        text="x",
        salt="abcd",
        emails=["a@b.com"],
        occurrences=[
            Occurrence(span="a@b.com", raw_llm="a@b.com", email="a@b.com", placeholder="E0_abcd")
        ],
    )
    assert result.occurrences[0].placeholder == "E0_abcd"


@pytest.mark.unit
def test_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        PIIEmail(text="x", unknown_field=1)


@pytest.mark.unit
def test_occurrence_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        Occurrence(span="x", raw_llm="x", unexpected=True)
