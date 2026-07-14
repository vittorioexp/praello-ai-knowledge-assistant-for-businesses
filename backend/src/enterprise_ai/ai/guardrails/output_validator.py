"""Structured output validation for agent responses."""

import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError as PydanticValidationError

from enterprise_ai.domain.exceptions import ValidationError


class AgentOutputSchema(BaseModel):
    """Expected structured agent output."""

    answer: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    tool_name: str | None = None
    tool_arguments: dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = False


class OutputValidator:
    """Validates and parses structured agent outputs."""

    def parse(self, raw: str) -> AgentOutputSchema:
        text = raw.strip()
        try:
            if text.startswith("{"):
                data = json.loads(text)
            else:
                start = text.find("{")
                end = text.rfind("}")
                if start == -1 or end == -1:
                    return AgentOutputSchema(answer=text, confidence=0.5)
                data = json.loads(text[start : end + 1])
            return AgentOutputSchema.model_validate(data)
        except (json.JSONDecodeError, PydanticValidationError) as exc:
            raise ValidationError("Agent returned invalid structured output") from exc

    def validate_business_rules(self, output: AgentOutputSchema) -> None:
        """Apply business rule filters."""
        blocked_terms = ["password", "secret_key", "api_key", "ssn", "credit card"]
        lower = output.answer.lower()
        for term in blocked_terms:
            if term in lower and "don't" not in lower:
                raise ValidationError(
                    f"Response blocked by business rule: sensitive term '{term}'"
                )
