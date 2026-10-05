"""Run one synchronization pass for registered connector accounts."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from enterprise_ai.application.services.connector_sync_service import ConnectorSyncService
from enterprise_ai.domain.repositories.document_connector import DocumentConnector
from enterprise_ai.infrastructure.database.models.connector_account import ConnectorAccountModel
from enterprise_ai.infrastructure.repositories.connector_account_repository import ConnectorAccountRepository
from enterprise_ai.infrastructure.security.connector_token_cipher import ConnectorTokenCipher
from enterprise_ai.infrastructure.config.settings import Settings
from enterprise_ai.infrastructure.connectors.oauth import refresh_access_token


class ConnectorFactory:
    """Build provider connectors from a persisted account."""

    def __init__(self, token_cipher: ConnectorTokenCipher) -> None:
        self._token_cipher = token_cipher

    def create(self, account: ConnectorAccountModel) -> DocumentConnector:
        from enterprise_ai.infrastructure.connectors.google_drive import GoogleDriveConnector
        from enterprise_ai.infrastructure.connectors.sharepoint import SharePointConnector

        token = self._token_cipher.decrypt(account.access_token_encrypted)
        if account.provider == "google_drive":
            return GoogleDriveConnector(token)
        if account.provider == "sharepoint":
            drive_id = account.provider_metadata.get("drive_id")
            if not drive_id:
                raise ValueError("SharePoint connector account is missing drive_id")
            return SharePointConnector(token, drive_id)
        raise ValueError(f"Unsupported connector provider: {account.provider}")


class ConnectorScheduler:
    """Synchronize all active accounts for one organization once."""

    def __init__(
        self,
        accounts: ConnectorAccountRepository,
        sync_service: ConnectorSyncService,
        factory: ConnectorFactory,
        settings: Settings,
    ) -> None:
        self._accounts = accounts
        self._sync_service = sync_service
        self._factory = factory
        self._settings = settings

    async def run_once(self, *, organization_id: UUID, uploaded_by: UUID) -> int:
        processed = 0
        for account in await self._accounts.list_active(organization_id):
            await self._refresh_if_needed(account)
            connector = self._factory.create(account)
            processed += await self._sync_service.sync_once(
                connector=connector,
                organization_id=organization_id,
                uploaded_by=uploaded_by,
                external_account_id=str(account.id),
            )
            await self._accounts.mark_synced(account, synced_at=datetime.now(UTC))
        return processed

    async def _refresh_if_needed(self, account: ConnectorAccountModel) -> None:
        if not account.refresh_token_encrypted:
            return
        if account.token_expires_at and account.token_expires_at > datetime.now(UTC) + timedelta(minutes=2):
            return
        cipher = self._factory._token_cipher  # noqa: SLF001
        refresh_token = cipher.decrypt(account.refresh_token_encrypted)
        tokens = await refresh_access_token(account.provider, refresh_token=refresh_token, settings=self._settings)
        account.access_token_encrypted = cipher.encrypt(tokens["access_token"])
        if tokens.get("refresh_token"):
            account.refresh_token_encrypted = cipher.encrypt(tokens["refresh_token"])
        account.token_expires_at = datetime.now(UTC) + timedelta(seconds=int(tokens.get("expires_in", 3600)))
