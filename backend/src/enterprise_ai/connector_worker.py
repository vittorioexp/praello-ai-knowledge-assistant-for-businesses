"""Periodic external connector synchronization worker."""

import asyncio
import os
from uuid import UUID

from enterprise_ai.ai.ingestion.chunking import ChunkingService
from enterprise_ai.api.dependencies import get_object_storage
from enterprise_ai.application.services.connector_scheduler import ConnectorFactory, ConnectorScheduler
from enterprise_ai.application.services.connector_sync_service import ConnectorSyncService
from enterprise_ai.application.services.document_service import DocumentService
from enterprise_ai.application.services.ingestion_service import IngestionService
from enterprise_ai.infrastructure.cache.redis_client import RedisClient
from enterprise_ai.infrastructure.config.settings import get_settings
from enterprise_ai.infrastructure.database.session import Database
from enterprise_ai.infrastructure.factories.ai_factory import create_embedding_service, create_vector_store
from enterprise_ai.infrastructure.logging.setup import configure_logging, get_logger
from enterprise_ai.infrastructure.queue.ingestion_queue import IngestionQueue
from enterprise_ai.infrastructure.repositories.connector_account_repository import ConnectorAccountRepository
from enterprise_ai.infrastructure.repositories.connector_sync_repository import ConnectorSyncRepository
from enterprise_ai.infrastructure.repositories.document_repository import SQLAlchemyDocumentRepository
from enterprise_ai.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from enterprise_ai.infrastructure.security.connector_token_cipher import ConnectorTokenCipher
from enterprise_ai.infrastructure.storage.file_storage import FileStorageService

logger = get_logger(__name__)


async def run() -> None:
    settings = get_settings()
    configured_organization = _optional_uuid("CONNECTOR_ORGANIZATION_ID")
    configured_uploaded_by = _optional_uuid("CONNECTOR_UPLOADED_BY")
    interval = int(os.getenv("CONNECTOR_SYNC_INTERVAL_SECONDS", "900"))
    configure_logging(debug=settings.app_debug)

    database = Database(settings)
    redis = RedisClient(settings)
    embeddings = create_embedding_service(settings)
    vector_store = create_vector_store(settings)
    queue = IngestionQueue(redis.client)
    object_storage = get_object_storage(settings)
    try:
        await vector_store.ensure_collection(embeddings.vector_size)
        while True:
            async for session in database.session():
                documents = SQLAlchemyDocumentRepository(session)
                ingestion = IngestionService(
                    documents,
                    embeddings,
                    vector_store,
                    ChunkingService(settings),
                    object_storage,
                )
                document_service = DocumentService(
                    documents,
                    FileStorageService(settings),
                    ingestion,
                    vector_store,
                    object_storage,
                )
                sync = ConnectorSyncService(
                    ConnectorSyncRepository(session),
                    document_service,
                    queue,
                )
                scheduler = ConnectorScheduler(
                    ConnectorAccountRepository(session),
                    sync,
                    ConnectorFactory(ConnectorTokenCipher(settings.app_secret_key)),
                    settings,
                )
                targets = await _sync_targets(
                    session,
                    organization_id=configured_organization,
                    uploaded_by=configured_uploaded_by,
                )
                for organization_id, uploaded_by in targets:
                    processed = await scheduler.run_once(
                        organization_id=organization_id,
                        uploaded_by=uploaded_by,
                    )
                    logger.info(
                        "connector_sync_cycle_completed",
                        organization_id=str(organization_id),
                        processed=processed,
                    )
            await asyncio.sleep(interval)
    finally:
        await database.dispose()
        await redis.close()
        if hasattr(vector_store, "_client"):
            await vector_store._client.close()  # noqa: SLF001


async def _sync_targets(
    session,
    *,
    organization_id: UUID | None,
    uploaded_by: UUID | None,
) -> list[tuple[UUID, UUID]]:
    if organization_id is not None and uploaded_by is not None:
        return [(organization_id, uploaded_by)]
    users = await SQLAlchemyUserRepository(session).list_all(limit=10_000)
    targets: dict[UUID, UUID] = {}
    for user in users:
        if user.is_active and user.organization_id is not None:
            targets.setdefault(user.organization_id, user.id)
    return list(targets.items())


def _optional_uuid(name: str) -> UUID | None:
    value = os.getenv(name)
    return UUID(value) if value else None


if __name__ == "__main__":
    asyncio.run(run())
