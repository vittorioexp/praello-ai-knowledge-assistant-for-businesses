"""Tests for initial and incremental connector cursors."""

import pytest

from enterprise_ai.infrastructure.connectors.google_drive import GoogleDriveConnector


class Response:
    status_code = 200
    headers: dict[str, str] = {}

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class DriveClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def get(self, url: str, *, params=None) -> Response:
        del params
        self.calls.append(url)
        if url == "/files":
            return Response(
                {
                    "files": [
                        {
                            "id": "file-1",
                            "name": "handbook.md",
                            "mimeType": "text/markdown",
                            "modifiedTime": "2026-01-01T00:00:00Z",
                            "version": "1",
                        }
                    ]
                }
            )
        return Response({"startPageToken": "delta-1"})


class PaginatedDriveClient(DriveClient):
    async def get(self, url: str, *, params=None) -> Response:
        del params
        self.calls.append(url)
        if url == "/files":
            return Response({"files": [], "nextPageToken": "page-2"})
        return Response({"startPageToken": "delta-2"})


@pytest.mark.asyncio
async def test_initial_drive_sync_returns_changes_cursor() -> None:
    client = DriveClient()
    connector = GoogleDriveConnector("token", http_client=client)  # type: ignore[arg-type]

    documents, cursor = await connector.list_changes(None)

    assert len(documents) == 1
    assert cursor == "changes:delta-1"
    assert client.calls == ["/files", "/changes/startPageToken"]


def test_drive_deleted_file_becomes_tombstone() -> None:
    connector = GoogleDriveConnector("token")

    tombstone = connector._tombstone(  # noqa: SLF001
        {"id": "deleted-1", "name": "old.md", "mimeType": "text/markdown"}
    )

    assert tombstone.deleted is True
    assert tombstone.content is None
    assert tombstone.source_id == "google-drive"
    assert tombstone.item_id == "deleted-1"


@pytest.mark.asyncio
async def test_initial_drive_sync_preserves_files_pagination_cursor() -> None:
    client = PaginatedDriveClient()
    connector = GoogleDriveConnector("token", http_client=client)  # type: ignore[arg-type]

    documents, cursor = await connector.list_changes(None)

    assert documents == []
    assert cursor == "files:page-2"
    assert client.calls == ["/files"]
