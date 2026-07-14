"""Instrumented LLM wrapper with caching, tracking, and retry."""

import asyncio
import time
from typing import Any

from enterprise_ai.ai.llm.cache import LLMCache
from enterprise_ai.ai.llm.router import ModelRouter
from enterprise_ai.ai.llm.usage_tracker import LLMUsageTracker, estimate_tokens
from enterprise_ai.domain.repositories.llm_service import LLMService
from enterprise_ai.infrastructure.config.settings import Settings
from enterprise_ai.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)


class InstrumentedLLMService(LLMService):
    """Wraps an LLM service with LLMOps capabilities."""

    def __init__(
        self,
        inner: LLMService,
        tracker: LLMUsageTracker,
        cache: LLMCache,
        router: ModelRouter,
        settings: Settings,
    ) -> None:
        self._inner = inner
        self._tracker = tracker
        self._cache = cache
        self._router = router
        self._settings = settings
        self._model = getattr(inner, "_model", "mock")

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        operation: str = "generate",
    ) -> str:
        model = self._router.select_model(
            operation=operation,
            prompt_length=len(system_prompt) + len(user_prompt),
        )

        cached = await self._cache.get(model, system_prompt, user_prompt)
        if cached is not None:
            self._tracker.record(
                model=model,
                operation=operation,
                input_tokens=estimate_tokens(system_prompt + user_prompt),
                output_tokens=estimate_tokens(cached),
                cached=True,
            )
            return cached

        start = time.perf_counter()
        last_error: Exception | None = None
        max_retries = self._settings.llm_max_retries

        for attempt in range(max_retries + 1):
            try:
                result = await self._inner.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                )
                latency = time.perf_counter() - start
                self._tracker.record(
                    model=model,
                    operation=operation,
                    input_tokens=estimate_tokens(system_prompt + user_prompt),
                    output_tokens=estimate_tokens(result),
                    cached=False,
                    latency_seconds=latency,
                )
                await self._cache.set(model, system_prompt, user_prompt, result)
                return result
            except Exception as exc:
                last_error = exc
                if attempt < max_retries:
                    wait = 2**attempt
                    logger.warning(
                        "llm_retry",
                        attempt=attempt + 1,
                        error=str(exc),
                        wait=wait,
                    )
                    await asyncio.sleep(wait)

        if last_error:
            raise last_error
        return ""

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema_hint: str,
    ) -> dict[str, Any]:
        return await self._inner.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema_hint=schema_hint,
        )
