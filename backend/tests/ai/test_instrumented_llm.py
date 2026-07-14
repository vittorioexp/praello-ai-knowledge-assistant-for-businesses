"""Tests for instrumented LLM service."""

import pytest

from enterprise_ai.ai.llm.cache import LLMCache
from enterprise_ai.ai.llm.instrumented import InstrumentedLLMService
from enterprise_ai.ai.llm.mock_llm import MockLLMService
from enterprise_ai.ai.llm.router import ModelRouter
from enterprise_ai.ai.llm.usage_tracker import LLMUsageTracker
from enterprise_ai.infrastructure.cache.redis_client import RedisClient
from enterprise_ai.infrastructure.config.settings import Settings


@pytest.fixture
def instrumented_llm(test_settings, mock_redis) -> InstrumentedLLMService:
    inner = MockLLMService()
    inner._model = "mock"  # type: ignore[attr-defined]
    test_settings.llm_cache_enabled = False
    return InstrumentedLLMService(
        inner,
        LLMUsageTracker(),
        LLMCache(mock_redis, test_settings),
        ModelRouter(test_settings),
        test_settings,
    )


@pytest.mark.asyncio
async def test_instrumented_llm_tracks_usage(instrumented_llm: InstrumentedLLMService) -> None:
    result = await instrumented_llm.generate(
        system_prompt="You are helpful",
        user_prompt="Hello",
    )
    assert result
    summary = instrumented_llm._tracker.get_summary()
    assert summary["total_requests"] >= 1


@pytest.mark.asyncio
async def test_model_router_selects_by_operation(test_settings: Settings) -> None:
    router = ModelRouter(test_settings)
    assert router.select_model(operation="embedding", prompt_length=100) == test_settings.openai_model
    assert router.select_model(operation="agent", prompt_length=5000) == test_settings.openai_complex_model
