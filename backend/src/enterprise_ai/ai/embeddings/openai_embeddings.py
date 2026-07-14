"""OpenAI embedding service implementation."""

from openai import AsyncOpenAI

from enterprise_ai.domain.exceptions import ValidationError
from enterprise_ai.domain.repositories.embedding_service import EmbeddingService
from enterprise_ai.infrastructure.config.settings import Settings
from enterprise_ai.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)

# text-embedding-3-small default dimensions
_EMBEDDING_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class OpenAIEmbeddingService(EmbeddingService):
    """Generates embeddings via OpenAI API."""

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise ValidationError("OpenAI API key is not configured")
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_embedding_model
        self._vector_size = _EMBEDDING_DIMENSIONS.get(self._model, 1536)

    @property
    def vector_size(self) -> int:
        return self._vector_size

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = await self._client.embeddings.create(
            model=self._model,
            input=texts,
        )
        embeddings = [item.embedding for item in response.data]
        logger.info("embeddings_generated", count=len(embeddings), model=self._model)
        return embeddings
