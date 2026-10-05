"""Tests for provider retry behavior without network calls."""

from dataclasses import dataclass

import pytest

from enterprise_ai.infrastructure.connectors.google_drive import GoogleDriveConnector
from enterprise_ai.infrastructure.connectors.sharepoint import SharePointConnector


@dataclass
class FakeResponse:
    status_code: int
    headers: dict[str, str]


class FakeClient:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls = 0

    async def get(self, _url: str, *, params: dict[str, str] | None = None) -> FakeResponse:
        del params
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return response


@pytest.mark.asyncio
async def test_google_drive_retries_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("asyncio.sleep", _no_sleep)
    client = FakeClient(
        [
            FakeResponse(429, {"Retry-After": "0"}),
            FakeResponse(200, {}),
        ]
    )

    response = await GoogleDriveConnector._get_with_retry(client, "/test")  # type: ignore[arg-type]

    assert response.status_code == 200
    assert client.calls == 2


@pytest.mark.asyncio
async def test_sharepoint_stops_after_bounded_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("asyncio.sleep", _no_sleep)
    client = FakeClient([FakeResponse(503, {})])

    response = await SharePointConnector._get_with_retry(client, "/test")  # type: ignore[arg-type]

    assert response.status_code == 503
    assert client.calls == 4


async def _no_sleep(_seconds: float) -> None:
    return None
