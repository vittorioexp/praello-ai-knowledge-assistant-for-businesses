"""Tests for guardrails."""

import pytest

from enterprise_ai.ai.guardrails.output_validator import AgentOutputSchema, OutputValidator
from enterprise_ai.domain.exceptions import ValidationError


def test_output_validator_parses_json() -> None:
    raw = '{"answer": "Hello", "confidence": 0.9, "tool_name": null}'
    result = OutputValidator().parse(raw)
    assert result.answer == "Hello"
    assert result.confidence == 0.9


def test_business_rules_block_sensitive_terms() -> None:
    validator = OutputValidator()
    output = AgentOutputSchema(answer="Here is the api_key for production")
    with pytest.raises(ValidationError, match="business rule"):
        validator.validate_business_rules(output)
