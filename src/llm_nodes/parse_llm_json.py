"""Parse JSON from LLM replies (strip fences, validate with Pydantic)."""

import json

from pydantic import ValidationError


def parse_llm_json(answer: str, model_cls):
    raw = (answer or "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        return model_cls.model_validate(json.loads(raw))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from model: {e}") from e
    except ValidationError as e:
        raise ValueError(f"JSON does not match schema: {e}") from e
