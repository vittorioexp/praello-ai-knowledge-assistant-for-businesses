"""Incremental connector synchronization orchestration."""

from uuid import UUID

from enterprise_ai.domain.repositories.document_connector import DocumentConnector
from enterprise_ai.infrastructure.queue.ingestion_queue import IngestionQueue
from enterprise_ai.infrastructure.repositories.connector_sync_repository import ConnectorSyncRepository
from enterprise_ai.application.services.document_service import DocumentService


class ConnectorSyncService:
    """Synchronize one external account and enqueue changed documents."""

    def __init__(
        self,
        sync_states: ConnectorSyncRepository,
        documents: DocumentService,
        ingestion_queue: IngestionQueue,
    ) -> None:
        self._sync_states = sync_states
        self._documents = documents
        self._ingestion_queue = ingestion_queue

    async def sync_once(
        self,
        *,
        connector: DocumentConnector,
        organization_id: UUID,
        uploaded_by: UUID,
        external_account_id: str,
    ) -> int:
        state = await self._sync_states.get_or_create(
            organization_id=organization_id,
            connector_type=connector.__class__.__name__,
            external_account_id=external_account_id,
        )
        await self._sync_states.mark_started(state)
        try:
            changes, next_cursor = await connector.list_changes(state.cursor)
            processed = 0
            for remote in changes:
                if remote.deleted:
                    await self._documents.delete_by_source(remote.source_id, remote.item_id)
                else:
                    document = await self._documents.upsert_remote(
                        remote=remote,
                        uploaded_by=uploaded_by,
                        organization_id=organization_id,
                    )
                    await self._ingestion_queue.enqueue(document.id)
                processed += 1
            await self._sync_states.mark_completed(state, next_cursor)
            return processed
        except Exception as exc:
            await self._sync_states.mark_failed(state, str(exc))
            raise
