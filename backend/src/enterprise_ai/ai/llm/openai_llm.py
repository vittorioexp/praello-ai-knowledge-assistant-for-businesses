"""OpenAI LLM service."""

import json
import re
from typing import Any

from openai import AsyncOpenAI

from enterprise_ai.domain.exceptions import ValidationError
from enterprise_ai.domain.repositories.llm_service import LLMService
from enterprise_ai.infrastructure.config.settings import Settings
from enterprise_ai.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)


class OpenAILLMService(LLMService):
    """Generates text via OpenAI chat completions."""

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise ValidationError("OpenAI API key is not configured")
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model
        self._fallback = settings.openai_fallback_model

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.warning("llm_primary_failed", error=str(exc), fallback=self._fallback)
            response = await self._client.chat.completions.create(
                model=self._fallback,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
            )
            return response.choices[0].message.content or ""

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema_hint: str,
    ) -> dict[str, Any]:
        prompt = f"{user_prompt}\n\nRespond with valid JSON matching: {schema_hint}"
        raw = await self.generate(
            system_prompt=system_prompt,
            user_prompt=prompt,
            temperature=0.0,
        )
        return _parse_json(raw)


def _parse_json(text: str) -> dict[str, Any]:
    """Extract and parse JSON from LLM response."""
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationError("LLM returned invalid JSON") from exc
