"""Repository for tenant-owned connector accounts."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from enterprise_ai.infrastructure.database.models.connector_account import ConnectorAccountModel


class ConnectorAccountRepository:
    """Persist and query external accounts within an organization boundary."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active(self, organization_id: UUID) -> list[ConnectorAccountModel]:
        result = await self._session.execute(
            select(ConnectorAccountModel).where(
                ConnectorAccountModel.organization_id == organization_id,
                ConnectorAccountModel.is_active.is_(True),
            )
        )
        return list(result.scalars().all())

    async def get(
        self,
        *,
        organization_id: UUID,
        provider: str,
        external_account_id: str,
    ) -> ConnectorAccountModel | None:
        result = await self._session.execute(
            select(ConnectorAccountModel).where(
                ConnectorAccountModel.organization_id == organization_id,
                ConnectorAccountModel.provider == provider,
                ConnectorAccountModel.external_account_id == external_account_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, *, organization_id: UUID, account_id: UUID) -> ConnectorAccountModel | None:
        result = await self._session.execute(
            select(ConnectorAccountModel).where(
                ConnectorAccountModel.id == account_id,
                ConnectorAccountModel.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def save(self, account: ConnectorAccountModel) -> ConnectorAccountModel:
        self._session.add(account)
        await self._session.flush()
        return account

    async def deactivate(self, account: ConnectorAccountModel) -> None:
        account.is_active = False
        await self._session.flush()

    async def mark_synced(
        self,
        account: ConnectorAccountModel,
        *,
        synced_at: datetime,
    ) -> None:
        account.last_sync_at = synced_at
        await self._session.flush()
