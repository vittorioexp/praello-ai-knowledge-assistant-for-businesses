"""SharePoint and OneDrive connector using Microsoft Graph delta queries."""

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any
import asyncio

import httpx

from enterprise_ai.domain.repositories.document_connector import DocumentConnector, RemoteDocument


class SharePointConnector(DocumentConnector):
    """Read changed files from a Graph drive with delta pagination."""

    api_url = "https://graph.microsoft.com/v1.0"
    downloadable_types = {
        "application/pdf",
        "text/markdown",
        "text/plain",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    def __init__(
        self,
        access_token: str,
        drive_id: str,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._headers = {"Authorization": f"Bearer {access_token}"}
        self._drive_id = drive_id
        self._client = http_client

    async def list_changes(
        self, cursor: str | None
    ) -> tuple[list[RemoteDocument], str | None]:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(headers=self._headers, base_url=self.api_url)
        try:
            url = cursor or f"/drives/{self._drive_id}/root/delta"
            response = await self._get_with_retry(
                client,
                url,
                params=None if cursor else {"$select": "id,name,file,folder,lastModifiedDateTime,eTag,deleted,createdBy"},
            )
            response.raise_for_status()
            payload = response.json()
            documents: list[RemoteDocument] = []
            for item in payload.get("value", []):
                if item.get("deleted") is not None:
                    documents.append(self._tombstone(item))
                    continue
                file_data = item.get("file")
                if not file_data or file_data.get("mimeType") not in self.downloadable_types:
                    continue
                documents.append(await self._to_document(item, client))
            next_cursor = payload.get("@odata.nextLink") or payload.get("@odata.deltaLink")
            return documents, next_cursor
        finally:
            if owns_client:
                await client.aclose()

    async def _to_document(self, item: dict[str, Any], client: httpx.AsyncClient) -> RemoteDocument:
        modified_at = datetime.fromisoformat(item["lastModifiedDateTime"].replace("Z", "+00:00"))
        permissions = await self._permissions(item["id"], client)
        return RemoteDocument(
            source_id=f"sharepoint:{self._drive_id}",
            item_id=item["id"],
            name=item["name"],
            content_type=item["file"]["mimeType"],
            version=item.get("eTag", item["lastModifiedDateTime"]),
            modified_at=modified_at,
            content=self._download(item["id"]),
            permissions=tuple(permissions),
        )

    def _tombstone(self, item: dict[str, Any]) -> RemoteDocument:
        return RemoteDocument(
            source_id=f"sharepoint:{self._drive_id}",
            item_id=item["id"],
            name=item.get("name", "deleted"),
            content_type="application/octet-stream",
            version="deleted",
            modified_at=datetime.now().astimezone(),
            content=None,
            deleted=True,
        )

    async def _download(self, item_id: str) -> AsyncIterator[bytes]:
        async with httpx.AsyncClient(headers=self._headers, base_url=self.api_url) as client:
            async with client.stream(
                "GET",
                f"/drives/{self._drive_id}/items/{item_id}/content",
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(1024 * 1024):
                    yield chunk

    async def _permissions(self, item_id: str, client: httpx.AsyncClient) -> list[str]:
        response = await self._get_with_retry(
            client,
            f"/drives/{self._drive_id}/items/{item_id}/permissions",
            params={"$select": "grantedToV2,grantedToIdentitiesV2"},
        )
        response.raise_for_status()
        principals: list[str] = []
        for permission in response.json().get("value", []):
            identities = permission.get("grantedToIdentitiesV2", [])
            if identity := permission.get("grantedToV2"):
                identities.append(identity)
            for identity in identities:
                user = identity.get("user") or {}
                group = identity.get("group") or {}
                principals.extend(
                    value
                    for value in (
                        user.get("email"),
                        user.get("id"),
                        group.get("id"),
                    )
                    if value
                )
            link = permission.get("link") or {}
            if link:
                scope = link.get("scope")
                principals.append("link:anyone" if scope == "anonymous" else "link:organization")
        return list(dict.fromkeys(principals))

    @staticmethod
    async def _get_with_retry(
        client: httpx.AsyncClient,
        url: str,
        *,
        params: dict[str, str] | None = None,
        attempts: int = 4,
    ) -> httpx.Response:
        for attempt in range(attempts):
            response = await client.get(url, params=params)
            if response.status_code not in (429, *range(500, 600)):
                return response
            retry_after = response.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else 2**attempt
            await asyncio.sleep(min(delay, 60.0))
        return response

    @staticmethod
    def _principal_values(created_by: dict[str, Any] | None) -> list[str]:
        user = (created_by or {}).get("user") or {}
        return [value for value in (user.get("email"), user.get("id")) if value]
