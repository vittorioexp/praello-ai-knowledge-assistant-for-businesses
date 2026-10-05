"""Ingestion worker entrypoint."""

import asyncio
import os
from uuid import UUID

from enterprise_ai.ai.ingestion.chunking import ChunkingService
from enterprise_ai.application.services.ingestion_service import IngestionService
from enterprise_ai.infrastructure.config.settings import get_settings
from enterprise_ai.infrastructure.database.session import Database
from enterprise_ai.infrastructure.factories.ai_factory import (
    create_embedding_service,
    create_vector_store,
)
from enterprise_ai.infrastructure.logging.setup import configure_logging, get_logger
from enterprise_ai.infrastructure.queue.ingestion_queue import IngestionQueue
from enterprise_ai.infrastructure.repositories.document_repository import SQLAlchemyDocumentRepository
from enterprise_ai.infrastructure.storage.file_storage import FileStorageService
from enterprise_ai.infrastructure.cache.redis_client import RedisClient

logger = get_logger(__name__)


async def run() -> None:
    settings = get_settings()
    configure_logging(debug=settings.app_debug)
    database = Database(settings)
    redis = RedisClient(settings)
    embeddings = create_embedding_service(settings)
    vector_store = create_vector_store(settings)
    queue = IngestionQueue(redis.client)
    await queue.ensure_group()
    consumer = os.getenv("INGESTION_CONSUMER_NAME", "worker")

    try:
        await vector_store.ensure_collection(embeddings.vector_size)
        while True:
            messages = await queue.read(consumer)
            for message_id, fields in messages:
                document_id = UUID(fields["document_id"])
                try:
                    async for session in database.session():
                        service = IngestionService(
                            SQLAlchemyDocumentRepository(session),
                            embeddings,
                            vector_store,
                            ChunkingService(settings),
                        )
                        await service.ingest(document_id)
                    await queue.acknowledge(message_id)
                except Exception:
                    logger.exception(
                        "ingestion_worker_failed",
                        document_id=str(document_id),
                        message_id=message_id,
                    )
                    await queue.retry_or_dead_letter(
                        message_id,
                        fields,
                        max_attempts=settings.max_ingestion_attempts,
                        error="ingestion_failed",
                    )
    finally:
        await database.dispose()
        await redis.close()
        if hasattr(vector_store, "_client"):
            await vector_store._client.close()  # noqa: SLF001


if __name__ == "__main__":
    asyncio.run(run())
