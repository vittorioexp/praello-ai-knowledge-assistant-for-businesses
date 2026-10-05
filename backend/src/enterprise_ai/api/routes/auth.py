"""Authentication API routes."""

from datetime import UTC, datetime, timedelta
from typing import Annotated
from urllib.parse import urlencode
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from enterprise_ai.application.dto.auth import (
    LoginRequestDTO,
    RefreshTokenRequestDTO,
    RegisterRequestDTO,
    TokenResponseDTO,
    UserResponseDTO,
)
from enterprise_ai.application.services.auth_service import AuthService
from enterprise_ai.api.dependencies import get_app_settings, get_auth_service, get_current_user, get_db_session, get_jwt_service
from enterprise_ai.domain.entities.user import User
from enterprise_ai.domain.value_objects.role import Role
from enterprise_ai.infrastructure.config.settings import Settings
from enterprise_ai.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from enterprise_ai.infrastructure.security.jwt import JWTService
from enterprise_ai.infrastructure.security.password import hash_password
from enterprise_ai.infrastructure.security.saml import create_auth
from enterprise_ai.infrastructure.security.jwt import JWTService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


def _saml_request(request: Request) -> dict:
    return {
        "https": request.url.scheme == "https",
        "http_host": request.url.hostname,
        "server_port": request.url.port or (443 if request.url.scheme == "https" else 80),
        "script_name": request.url.path,
        "get_data": dict(request.query_params),
        "post_data": {},
    }


@router.get("/sso/saml/login")
async def saml_login(request: Request, settings: Annotated[Settings, Depends(get_app_settings)]) -> dict[str, str]:
    try:
        auth = create_auth(_saml_request(request), settings)
        return {"redirect_url": auth.login(return_to=settings.saml_acs_url)}
    except (ValueError, ImportError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/sso/saml/acs", response_model=TokenResponseDTO)
async def saml_acs(request: Request, session: Annotated[AsyncSession, Depends(get_db_session)], settings: Annotated[Settings, Depends(get_app_settings)], jwt_service: Annotated[JWTService, Depends(get_jwt_service)]) -> TokenResponseDTO:
    form = await request.form()
    saml_request = _saml_request(request)
    saml_request["post_data"] = dict(form)
    try:
        auth = create_auth(saml_request, settings)
        auth.process_response()
        if not auth.is_authenticated():
            raise HTTPException(status_code=401, detail="SAML authentication failed")
        email = auth.get_attribute("email") or auth.get_attribute("mail") or [auth.get_nameid()]
        name = (auth.get_attribute("displayName") or email)[0]
    except (ValueError, ImportError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    repository = SQLAlchemyUserRepository(session)
    user = await repository.get_by_email(email[0])
    if user is None:
        user = await repository.create(User(email=email[0], hashed_password=hash_password(uuid4().hex), full_name=name, role=Role.VIEWER))
    return TokenResponseDTO(access_token=jwt_service.create_access_token(user_id=user.id, email=user.email, role=user.role.value), refresh_token=jwt_service.create_refresh_token(user_id=user.id, email=user.email, role=user.role.value))


@router.get("/sso/oidc/authorize")
async def oidc_authorize(settings: Annotated[Settings, Depends(get_app_settings)]) -> dict[str, str]:
    if not settings.oidc_issuer_url or not settings.oidc_client_id or not settings.oidc_redirect_uri:
        raise HTTPException(status_code=503, detail="OIDC is not configured")
    async with httpx.AsyncClient(timeout=10) as client:
        metadata = (await client.get(f"{settings.oidc_issuer_url.rstrip('/')}/.well-known/openid-configuration")).json()
    state = jwt.encode({"nonce": str(uuid4()), "exp": datetime.now(UTC) + timedelta(minutes=10)}, settings.app_secret_key, algorithm="HS256")
    return {"authorization_url": f"{metadata['authorization_endpoint']}?{urlencode({'client_id': settings.oidc_client_id, 'redirect_uri': settings.oidc_redirect_uri, 'response_type': 'code', 'scope': 'openid profile email', 'state': state})}"}


@router.get("/sso/oidc/callback", response_model=TokenResponseDTO)
async def oidc_callback(code: str, state: str, session: Annotated[AsyncSession, Depends(get_db_session)], settings: Annotated[Settings, Depends(get_app_settings)], jwt_service: Annotated[JWTService, Depends(get_jwt_service)]) -> TokenResponseDTO:
    try:
        jwt.decode(state, settings.app_secret_key, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid SSO state") from exc
    async with httpx.AsyncClient(timeout=15) as client:
        metadata = (await client.get(f"{settings.oidc_issuer_url.rstrip('/')}/.well-known/openid-configuration")).json()
        response = await client.post(metadata["token_endpoint"], data={"grant_type": "authorization_code", "code": code, "client_id": settings.oidc_client_id, "client_secret": settings.oidc_client_secret, "redirect_uri": settings.oidc_redirect_uri})
        response.raise_for_status()
        tokens = response.json()
        userinfo = (await client.get(metadata["userinfo_endpoint"], headers={"Authorization": f"Bearer {tokens['access_token']}"})).json()
    email = userinfo.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="OIDC provider did not return an email")
    repository = SQLAlchemyUserRepository(session)
    user = await repository.get_by_email(email)
    if user is None:
        user = await repository.create(User(email=email, hashed_password=hash_password(uuid4().hex), full_name=userinfo.get("name", email), role=Role.VIEWER))
    return TokenResponseDTO(access_token=jwt_service.create_access_token(user_id=user.id, email=user.email, role=user.role.value), refresh_token=jwt_service.create_refresh_token(user_id=user.id, email=user.email, role=user.role.value))


@router.post("/register", response_model=UserResponseDTO, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequestDTO,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponseDTO:
    """Register a new user account."""
    return await auth_service.register(request)


@router.post("/login", response_model=TokenResponseDTO)
async def login(
    request: LoginRequestDTO,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponseDTO:
    """Authenticate and receive JWT tokens."""
    return await auth_service.login(request)


@router.post("/refresh", response_model=TokenResponseDTO)
async def refresh(
    request: RefreshTokenRequestDTO,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponseDTO:
    """Refresh access token using a valid refresh token."""
    return await auth_service.refresh_token(request.refresh_token)


@router.get("/me", response_model=UserResponseDTO)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponseDTO:
    """Get the currently authenticated user."""
    return AuthService.to_response(current_user)
