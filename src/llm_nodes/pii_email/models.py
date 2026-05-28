"""Structured output for the PII email extraction node."""

from pydantic import EmailStr, Field, TypeAdapter, ValidationError, field_validator, model_validator

from ..base_state import BaseState


class PIIEmail(BaseState):
    """Redacted text (EMAILn placeholders) and original addresses in order."""

    text: str = Field(default="")
    recognized_emails: list[str] = Field(default_factory=list)
    raw_emails: list[str] = Field(default_factory=list)
    normalized_emails: list[EmailStr | None] = Field(default_factory=list)

    @field_validator("raw_emails", mode="before")
    @classmethod
    def validate_raw_emails(cls, v):
        return [email.strip().lower() for email in v]

    @field_validator("recognized_emails", mode="before")
    @classmethod
    def validate_recognized_emails(cls, v):
        return [email.strip() for email in v]

    @model_validator(mode="after")
    def validate_normalized_emails(self):
        adapter = TypeAdapter(EmailStr)
        out: list[EmailStr | None] = []
        for raw_email in self.raw_emails:
            try:
                out.append(adapter.validate_python(raw_email))
            except ValidationError:
                out.append(None)
        self.normalized_emails = out

        if len(self.recognized_emails) != len(self.raw_emails):
            raise ValueError("recognized_emails and raw_emails must have the same length")

        if len(self.recognized_emails) != len(self.normalized_emails):
            raise ValueError("recognized_emails and normalized_emails must have the same length")

        return self
