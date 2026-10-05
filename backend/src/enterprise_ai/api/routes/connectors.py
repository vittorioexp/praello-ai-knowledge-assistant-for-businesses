"""Connector account lifecycle API."""

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
import httpx
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from enterprise_ai.api.dependencies import get_app_settings, get_current_user, get_db_session
from enterprise_ai.api.middleware.rbac import require_permission
from enterprise_ai.domain.entities.user import User
from enterprise_ai.domain.value_objects.role import Permission
from enterprise_ai.infrastructure.config.settings import Settings
from enterprise_ai.infrastructure.database.models.connector_account import ConnectorAccountModel
from enterprise_ai.infrastructure.repositories.connector_account_repository import ConnectorAccountRepository
from enterprise_ai.infrastructure.security.connector_token_cipher import ConnectorTokenCipher
from enterprise_ai.infrastructure.connectors.oauth import (
    OAuthConfigurationError,
    authorization_url,
    exchange_code,
    external_account_id,
)

router = APIRouter(prefix="/connectors", tags=["Connectors"])


class ConnectorAccountCreateRequest(BaseModel):
    provider: str = Field(pattern="^(google_drive|sharepoint)$")
    external_account_id: str = Field(min_length=1, max_length=512)
    access_token: str = Field(min_length=1)
    refresh_token: str | None = None
    provider_metadata: dict = Field(default_factory=dict)
    token_expires_at: datetime | None = None


class ConnectorAccountResponse(BaseModel):
    id: UUID
    provider: str
    external_account_id: str
    provider_metadata: dict
    is_active: bool
    token_expires_at: datetime | None
    last_sync_at: datetime | None


@router.get("/{provider}/authorize")
async def authorize_connector(
    provider: str,
    current_user: Annotated[User, Depends(require_permission(Permission.CONNECTORS_MANAGE.value))],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> dict[str, str]:
    """Build a signed OAuth state and provider authorization URL."""
    if current_user.organization_id is None:
        raise HTTPException(status_code=400, detail="User has no organization")
    state = jwt.encode(
        {"user_id": str(current_user.id), "organization_id": str(current_user.organization_id), "provider": provider, "exp": datetime.now(UTC) + timedelta(minutes=10)},
        settings.app_secret_key,
        algorithm="HS256",
    )
    try:
        return {"authorization_url": authorization_url(provider, state=state, settings=settings)}
    except OAuthConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{provider}/callback", response_model=ConnectorAccountResponse)
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> ConnectorAccountResponse:
    try:
        claims = jwt.decode(state, settings.app_secret_key, algorithms=["HS256"])
        if claims.get("provider") != provider:
            raise ValueError("OAuth provider mismatch")
        organization_id = UUID(claims["organization_id"])
        uploaded_by = UUID(claims["user_id"])
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state") from exc
    try:
        tokens = await exchange_code(provider, code=code, settings=settings)
        access_token = tokens["access_token"]
        account_id = await external_account_id(provider, access_token=access_token)
    except (httpx.HTTPError, KeyError, OAuthConfigurationError) as exc:
        raise HTTPException(status_code=502, detail="OAuth provider exchange failed") from exc
    repository = ConnectorAccountRepository(session)
    account = await repository.get(
        organization_id=organization_id, provider=provider, external_account_id=account_id
    )
    cipher = ConnectorTokenCipher(settings.app_secret_key)
    if account is None:
        account = ConnectorAccountModel(
            organization_id=organization_id,
            provider=provider,
            external_account_id=account_id,
            access_token_encrypted=cipher.encrypt(access_token),
            refresh_token_encrypted=(cipher.encrypt(tokens["refresh_token"]) if tokens.get("refresh_token") else None),
            provider_metadata={},
        )
        await repository.save(account)
    else:
        account.access_token_encrypted = cipher.encrypt(access_token)
        if tokens.get("refresh_token"):
            account.refresh_token_encrypted = cipher.encrypt(tokens["refresh_token"])
        account.is_active = True
        await session.flush()
    return _response(account)


def _response(account: ConnectorAccountModel) -> ConnectorAccountResponse:
    return ConnectorAccountResponse.model_validate(account, from_attributes=True)


@router.post("", response_model=ConnectorAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_connector(
    request: ConnectorAccountCreateRequest,
    current_user: Annotated[User, Depends(require_permission(Permission.CONNECTORS_MANAGE.value))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> ConnectorAccountResponse:
    if current_user.organization_id is None:
        raise HTTPException(status_code=400, detail="User has no organization")
    repository = ConnectorAccountRepository(session)
    existing = await repository.get(
        organization_id=current_user.organization_id,
        provider=request.provider,
        external_account_id=request.external_account_id,
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Connector account already exists")
    cipher = ConnectorTokenCipher(settings.app_secret_key)
    account = ConnectorAccountModel(
        organization_id=current_user.organization_id,
        provider=request.provider,
        external_account_id=request.external_account_id,
        access_token_encrypted=cipher.encrypt(request.access_token),
        refresh_token_encrypted=cipher.encrypt(request.refresh_token) if request.refresh_token else None,
        provider_metadata=request.provider_metadata,
        token_expires_at=request.token_expires_at,
    )
    return _response(await repository.save(account))


@router.get("", response_model=list[ConnectorAccountResponse])
async def list_connectors(
    current_user: Annotated[User, Depends(require_permission(Permission.CONNECTORS_READ.value))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ConnectorAccountResponse]:
    if current_user.organization_id is None:
        return []
    accounts = await ConnectorAccountRepository(session).list_active(current_user.organization_id)
    return [_response(account) for account in accounts]


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_connector(
    account_id: UUID,
    current_user: Annotated[User, Depends(require_permission(Permission.CONNECTORS_MANAGE.value))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    if current_user.organization_id is None:
        raise HTTPException(status_code=404, detail="Connector account not found")
    repository = ConnectorAccountRepository(session)
    account = await repository.get_by_id(organization_id=current_user.organization_id, account_id=account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Connector account not found")
    await repository.deactivate(account)