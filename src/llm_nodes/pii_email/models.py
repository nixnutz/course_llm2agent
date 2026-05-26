"""Structured output for the PII email extraction node."""

from pydantic import BaseModel, Field


class PIIEmail(BaseModel):
    """Redacted text (EMAILn placeholders) and original addresses in order."""

    text: str = Field(default="")
    emails: list[str] = Field(default_factory=list)
