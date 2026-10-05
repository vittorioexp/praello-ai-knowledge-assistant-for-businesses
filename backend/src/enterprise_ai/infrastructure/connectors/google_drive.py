"""Google Drive incremental document connector."""

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any
import asyncio

import httpx

from enterprise_ai.domain.repositories.document_connector import DocumentConnector, RemoteDocument


class GoogleDriveConnector(DocumentConnector):
    """Read changed Google Drive files using the Drive API v3."""

    api_url = "https://www.googleapis.com/drive/v3"
    downloadable_types = {
        "application/pdf",
        "text/markdown",
        "text/plain",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    def __init__(self, access_token: str, *, http_client: httpx.AsyncClient | None = None) -> None:
        self._headers = {"Authorization": f"Bearer {access_token}"}
        self._client = http_client

    async def list_changes(
        self, cursor: str | None
    ) -> tuple[list[RemoteDocument], str | None]:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(headers=self._headers, base_url=self.api_url)
        try:
            if cursor is None or cursor.startswith("files:"):
                page_token = cursor.removeprefix("files:") if cursor else None
                response = await self._get_with_retry(
                    client,
                    "/files",
                    params={
                        "pageToken": page_token,
                        "pageSize": 1000,
                        "spaces": "drive",
                        "q": "trashed = false",
                        "fields": "nextPageToken,files(id,name,mimeType,modifiedTime,version,trashed,permissions(id,type,emailAddress,domain,allowFileDiscovery))",
                    },
                )
                response.raise_for_status()
                payload = response.json()
                documents = [
                    self._to_document(file_data, client)
                    for file_data in payload.get("files", [])
                    if file_data.get("mimeType") in self.downloadable_types
                ]
                next_page = payload.get("nextPageToken")
                if next_page:
                    return documents, f"files:{next_page}"
                token_response = await self._get_with_retry(client, "/changes/startPageToken")
                token_response.raise_for_status()
                return documents, f"changes:{token_response.json()['startPageToken']}"

            cursor = cursor.removeprefix("changes:")
            page_token = cursor
            if page_token is None:
                response = await self._get_with_retry(client, "/changes/startPageToken")
                response.raise_for_status()
                page_token = response.json()["startPageToken"]

            response = await self._get_with_retry(
                client,
                "/changes",
                params={
                    "pageToken": page_token,
                    "includeRemoved": "true",
                    "spaces": "drive",
                        "fields": "nextPageToken,newStartPageToken,changes(file(id,name,mimeType,modifiedTime,version,trashed,webContentLink,permissions(id,type,emailAddress,domain,allowFileDiscovery)))",
                },
            )
            response.raise_for_status()
            payload = response.json()
            documents: list[RemoteDocument] = []
            for change in payload.get("changes", []):
                file_data = change.get("file")
                if not file_data:
                    if change.get("removed") and change.get("fileId"):
                        documents.append(
                            RemoteDocument(
                                source_id="google-drive",
                                item_id=change["fileId"],
                                name="deleted",
                                content_type="application/octet-stream",
                                version="deleted",
                                modified_at=datetime.now().astimezone(),
                                content=None,
                                deleted=True,
                            )
                        )
                    continue
                if file_data.get("trashed"):
                    documents.append(
                        RemoteDocument(
                            source_id="google-drive",
                            item_id=file_data["id"],
                            name=file_data.get("name", "deleted"),
                            content_type=file_data.get("mimeType", "application/octet-stream"),
                            version=str(file_data.get("version", "deleted")),
                            modified_at=datetime.now().astimezone(),
                            content=None,
                            deleted=True,
                        )
                    )
                    continue
                if file_data.get("mimeType") not in self.downloadable_types:
                    continue
                documents.append(self._to_document(file_data, client))
            next_cursor = payload.get("nextPageToken") or payload.get("newStartPageToken")
            return documents, f"changes:{next_cursor}" if next_cursor else None
        finally:
            if owns_client:
                await client.aclose()

    def _to_document(self, file_data: dict[str, Any], client: httpx.AsyncClient) -> RemoteDocument:
        modified_at = datetime.fromisoformat(file_data["modifiedTime"].replace("Z", "+00:00"))
        return RemoteDocument(
            source_id="google-drive",
            item_id=file_data["id"],
            name=file_data["name"],
            content_type=file_data["mimeType"],
            version=str(file_data.get("version", file_data["modifiedTime"])),
            modified_at=modified_at,
            content=self._download(file_data["id"]),
            permissions=tuple(self._permission_principals(file_data.get("permissions", []))),
        )

    @staticmethod
    def _permission_principals(permissions: list[dict[str, Any]]) -> list[str]:
        principals: list[str] = []
        for permission in permissions:
            permission_type = permission.get("type")
            if permission_type == "user" and permission.get("emailAddress"):
                principals.append(permission["emailAddress"])
            elif permission_type == "group" and permission.get("emailAddress"):
                principals.append(f"group:{permission['emailAddress']}")
            elif permission_type == "domain":
                principals.append(f"domain:{permission.get('domain', '')}")
            elif permission_type == "anyone":
                principals.append("link:anyone" if permission.get("allowFileDiscovery") else "link:authenticated")
        return list(dict.fromkeys(principals))

    def _tombstone(self, file_data: dict[str, Any]) -> RemoteDocument:
        return RemoteDocument(
            source_id="google-drive",
            item_id=file_data["id"],
            name=file_data.get("name", "deleted"),
            content_type=file_data.get("mimeType", "application/octet-stream"),
            version="deleted",
            modified_at=datetime.now().astimezone(),
            content=None,
            deleted=True,
        )

    async def _download(self, file_id: str) -> AsyncIterator[bytes]:
        async with httpx.AsyncClient(headers=self._headers, base_url=self.api_url) as client:
            async with client.stream(
                "GET",
                f"/files/{file_id}",
                params={"alt": "media"},
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(1024 * 1024):
                    yield chunk

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
