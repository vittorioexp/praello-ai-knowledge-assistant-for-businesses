"""Repository for connector synchronization cursors."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from enterprise_ai.infrastructure.database.models.connector_sync_state import ConnectorSyncStateModel


class ConnectorSyncRepository:
    """Persist connector progress and operational status."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self,
        *,
        organization_id: UUID,
        connector_type: str,
        external_account_id: str,
    ) -> ConnectorSyncStateModel | None:
        result = await self._session.execute(
            select(ConnectorSyncStateModel).where(
                ConnectorSyncStateModel.organization_id == organization_id,
                ConnectorSyncStateModel.connector_type == connector_type,
                ConnectorSyncStateModel.external_account_id == external_account_id,
            )
        )
        return result.scalar_one_or_none()

    async def mark_started(self, state: ConnectorSyncStateModel) -> None:
        state.status = "running"
        state.last_error = None
        state.last_started_at = datetime.now(UTC)
        await self._session.flush()

    async def get_or_create(
        self,
        *,
        organization_id: UUID,
        connector_type: str,
        external_account_id: str,
    ) -> ConnectorSyncStateModel:
        state = await self.get(
            organization_id=organization_id,
            connector_type=connector_type,
            external_account_id=external_account_id,
        )
        if state is None:
            state = ConnectorSyncStateModel(
                organization_id=organization_id,
                connector_type=connector_type,
                external_account_id=external_account_id,
            )
            self._session.add(state)
            await self._session.flush()
        return state

    async def mark_completed(self, state: ConnectorSyncStateModel, cursor: str | None) -> None:
        state.cursor = cursor
        state.status = "idle"
        state.last_error = None
        state.last_completed_at = datetime.now(UTC)
        await self._session.flush()

    async def mark_failed(self, state: ConnectorSyncStateModel, error: str) -> None:
        state.status = "failed"
        state.last_error = error[:10_000]
        await self._session.flush()
