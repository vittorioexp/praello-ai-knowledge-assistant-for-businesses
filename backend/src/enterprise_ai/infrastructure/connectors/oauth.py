"""Provider OAuth authorization URL builders."""

from urllib.parse import urlencode

import httpx

from enterprise_ai.infrastructure.config.settings import Settings


class OAuthConfigurationError(ValueError):
    """Raised when a provider OAuth integration is not configured."""


async def exchange_code(provider: str, *, code: str, settings: Settings) -> dict:
    if provider == "google_drive":
        url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": settings.google_oauth_client_id,
            "client_secret": settings.google_oauth_client_secret,
            "redirect_uri": settings.google_oauth_redirect_uri,
            "grant_type": "authorization_code",
        }
    elif provider == "sharepoint":
        url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        data = {
            "code": code,
            "client_id": settings.microsoft_oauth_client_id,
            "client_secret": settings.microsoft_oauth_client_secret,
            "redirect_uri": settings.microsoft_oauth_redirect_uri,
            "grant_type": "authorization_code",
            "scope": "offline_access Files.Read.All User.Read",
        }
    else:
        raise OAuthConfigurationError(f"Unsupported connector provider: {provider}")
    if not data["client_id"] or not data["client_secret"] or not data["redirect_uri"]:
        raise OAuthConfigurationError(f"OAuth is not configured for {provider}")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(url, data=data)
        response.raise_for_status()
        return response.json()


async def external_account_id(provider: str, *, access_token: str) -> str:
    url = "https://www.googleapis.com/drive/v3/about?fields=user(emailAddress)" if provider == "google_drive" else "https://graph.microsoft.com/v1.0/me?$select=id,userPrincipalName"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
        response.raise_for_status()
        payload = response.json()
    if provider == "google_drive":
        return payload["user"]["emailAddress"]
    return payload.get("userPrincipalName") or payload["id"]


async def refresh_access_token(provider: str, *, refresh_token: str, settings: Settings) -> dict:
    if provider == "google_drive":
        url = "https://oauth2.googleapis.com/token"
        data = {"client_id": settings.google_oauth_client_id, "client_secret": settings.google_oauth_client_secret, "refresh_token": refresh_token, "grant_type": "refresh_token"}
    elif provider == "sharepoint":
        url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        data = {"client_id": settings.microsoft_oauth_client_id, "client_secret": settings.microsoft_oauth_client_secret, "refresh_token": refresh_token, "grant_type": "refresh_token", "scope": "offline_access Files.Read.All User.Read"}
    else:
        raise OAuthConfigurationError(f"Unsupported connector provider: {provider}")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(url, data=data)
        response.raise_for_status()
        return response.json()


def authorization_url(provider: str, *, state: str, settings: Settings) -> str:
    if provider == "google_drive":
        client_id, redirect_uri = settings.google_oauth_client_id, settings.google_oauth_redirect_uri
        endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/drive.readonly",
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
    elif provider == "sharepoint":
        client_id, redirect_uri = settings.microsoft_oauth_client_id, settings.microsoft_oauth_redirect_uri
        endpoint = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "response_mode": "query",
            "scope": "offline_access Files.Read.All User.Read",
            "state": state,
        }
    else:
        raise OAuthConfigurationError(f"Unsupported connector provider: {provider}")
    if not client_id or not redirect_uri:
        raise OAuthConfigurationError(f"OAuth is not configured for {provider}")
    return f"{endpoint}?{urlencode(params)}"