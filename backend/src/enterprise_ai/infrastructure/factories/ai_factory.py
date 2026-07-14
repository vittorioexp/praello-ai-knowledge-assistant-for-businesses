"""Factory for AI infrastructure components."""

from enterprise_ai.ai.embeddings.mock_embeddings import MockEmbeddingService
from enterprise_ai.ai.embeddings.openai_embeddings import OpenAIEmbeddingService
from enterprise_ai.ai.llm.cache import LLMCache
from enterprise_ai.ai.llm.instrumented import InstrumentedLLMService
from enterprise_ai.ai.llm.mock_llm import MockLLMService
from enterprise_ai.ai.llm.openai_llm import OpenAILLMService
from enterprise_ai.ai.llm.router import ModelRouter
from enterprise_ai.ai.llm.usage_tracker import LLMUsageTracker
from enterprise_ai.domain.repositories.embedding_service import EmbeddingService
from enterprise_ai.domain.repositories.llm_service import LLMService
from enterprise_ai.domain.repositories.vector_store import VectorStore
from enterprise_ai.infrastructure.cache.redis_client import RedisClient
from enterprise_ai.infrastructure.config.settings import Settings
from enterprise_ai.infrastructure.vector_store.in_memory_store import InMemoryVectorStore
from enterprise_ai.infrastructure.vector_store.qdrant_store import QdrantVectorStore


def create_embedding_service(settings: Settings) -> EmbeddingService:
    """Create embedding service based on environment."""
    if settings.is_test or not settings.openai_api_key:
        return MockEmbeddingService()
    return OpenAIEmbeddingService(settings)


def create_vector_store(settings: Settings) -> VectorStore:
    """Create vector store based on environment."""
    if settings.is_test:
        return InMemoryVectorStore()
    return QdrantVectorStore(settings)


def create_llm_tracker() -> LLMUsageTracker:
    return LLMUsageTracker()


def create_llm_service(
    settings: Settings,
    redis: RedisClient | None = None,
    tracker: LLMUsageTracker | None = None,
) -> LLMService:
    """Create instrumented LLM service based on environment."""
    if settings.is_test or not settings.openai_api_key:
        inner: LLMService = MockLLMService()
        inner._model = "mock"  # type: ignore[attr-defined]
    else:
        inner = OpenAILLMService(settings)

    _tracker = tracker or create_llm_tracker()
    _redis = redis or RedisClient(settings)
    cache = LLMCache(_redis, settings)
    router = ModelRouter(settings)

    return InstrumentedLLMService(inner, _tracker, cache, router, settings)
