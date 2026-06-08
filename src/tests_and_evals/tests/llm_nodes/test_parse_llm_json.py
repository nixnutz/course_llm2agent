"""Tests for ``ParseLLMJson`` (minimal, schema-agnostic coverage).

Summary:
- Plain JSON and markdown-fenced JSON -> dict via ``parse_as_dict``.
- Whitespace strip on the outer answer string.
- Empty / invalid payload -> ``Invalid JSON from model``.
- Partial objects: missing keys are absent (callers apply field defaults).
- ``parse_as_model``: Pydantic validation and wrapped schema errors (generic model).

Domain-specific shapes (e.g. ``PIIEmail``) belong in that node's tests, not here.

Not exhaustive: course/WIP helper; expand when LLM reply formats stabilize.
"""

import json

from pydantic import BaseModel, ValidationError
import pytest

from src.errors import PipelineValidationError
from src.llm_nodes.parse_llm_json import ParseLLMJson

_SAMPLE = {"answer": "ok", "count": 2}


class _MiniModel(BaseModel):
    answer: str
    count: int = 0


@pytest.mark.unit
def test_parse_as_dict_plain_json():
    payload = json.dumps(_SAMPLE)
    assert ParseLLMJson().parse_as_dict(payload) == _SAMPLE


@pytest.mark.unit
def test_parse_as_dict_markdown_fence():
    payload = json.dumps(_SAMPLE)
    fenced = f"```json\n{payload}\n```"
    assert ParseLLMJson().parse_as_dict(fenced) == _SAMPLE


@pytest.mark.unit
def test_parse_as_dict_strips_outer_whitespace():
    payload = json.dumps(_SAMPLE)
    assert ParseLLMJson().parse_as_dict(f"  {payload}  ") == _SAMPLE


@pytest.mark.unit
def test_parse_as_dict_empty_raises_invalid_json():
    with pytest.raises(PipelineValidationError, match="Invalid JSON from model"):
        ParseLLMJson().parse_as_dict("")


@pytest.mark.unit
def test_parse_as_dict_whitespace_only_raises_invalid_json():
    with pytest.raises(PipelineValidationError, match="Invalid JSON from model"):
        ParseLLMJson().parse_as_dict("   \n  ")


@pytest.mark.unit
def test_parse_as_dict_missing_keys_returns_partial():
    result = ParseLLMJson().parse_as_dict('{"answer": "only"}')
    assert result == {"answer": "only"}
    assert "count" not in result


@pytest.mark.unit
def test_parse_as_model_valid():
    payload = json.dumps(_SAMPLE)
    parsed = ParseLLMJson().parse_as_model(payload, _MiniModel)
    assert parsed.answer == "ok"
    assert parsed.count == 2


@pytest.mark.unit
def test_parse_as_model_schema_mismatch():
    bad = json.dumps({"answer": "ok", "count": "not-a-number"})
    with pytest.raises(PipelineValidationError, match="JSON does not match schema") as exc_info:
        ParseLLMJson().parse_as_model(bad, _MiniModel)
    assert isinstance(exc_info.value.__cause__, ValidationError)
