"""Parse JSON from LLM replies (strip fences, validate with Pydantic)."""

import json

from pydantic import BaseModel, ValidationError


class ParseLLMJson:
    """Parse JSON from LLM replies (strip fences, validate with Pydantic)."""

    def _extract_json(self, answer: str) -> dict:
        """Extract JSON from LLM reply, stripping fences and validating."""
        raw = (answer or "").strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from model: {e}") from e

    def parse_as_model(self, answer: str, model_cls: type[BaseModel]) -> BaseModel:
        """Parse JSON from LLM reply as a Pydantic model."""
        try:
            return model_cls.model_validate(self._extract_json(answer))
        except ValidationError as e:
            raise ValueError(f"JSON does not match schema: {e}") from e

    def parse_as_dict(self, answer: str) -> dict:
        """Parse JSON from LLM reply as a dictionary."""
        return self._extract_json(answer)
