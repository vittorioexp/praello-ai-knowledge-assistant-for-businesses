"""Tests for document API endpoints."""

import asyncio

import pytest
from httpx import AsyncClient


SAMPLE_MARKDOWN = b"""# Company Policy

## Remote Work
Employees may work remotely up to 3 days per week.

## Security
Enable MFA on all accounts.
"""


@pytest.mark.asyncio
async def test_upload_markdown_document(
    client: AsyncClient,
    contributor_token: str,
) -> None:
    response = await client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {contributor_token}"},
        files={"file": ("policy.md", SAMPLE_MARKDOWN, "text/markdown")},
        data={"metadata": '{"tags": ["policy", "hr"]}'},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "policy.md"
    assert data["document_type"] == "markdown"
    assert "policy" in data["tags"]
    await asyncio.sleep(0.1)
    doc_id = data["id"]
    get_resp = await client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {contributor_token}"},
    )
    assert get_resp.status_code == 200


@pytest.mark.asyncio
async def test_upload_requires_permission(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "viewer@company.com",
            "password": "securepass123",
            "full_name": "Viewer",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@company.com", "password": "securepass123"},
    )
    token = login.json()["access_token"]

    response = await client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("policy.md", SAMPLE_MARKDOWN, "text/markdown")},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_documents(
    client: AsyncClient,
    contributor_token: str,
) -> None:
    await client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {contributor_token}"},
        files={"file": ("list-test.md", SAMPLE_MARKDOWN, "text/markdown")},
    )
    response = await client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {contributor_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_delete_document(
    client: AsyncClient,
    admin_token: str,
    contributor_token: str,
) -> None:
    upload_resp = await client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {contributor_token}"},
        files={"file": ("delete-me.md", SAMPLE_MARKDOWN, "text/markdown")},
    )
    doc_id = upload_resp.json()["id"]

    response = await client.delete(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204

    get_resp = await client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {contributor_token}"},
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_upload_unsupported_type(
    client: AsyncClient,
    contributor_token: str,
) -> None:
    response = await client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {contributor_token}"},
        files={"file": ("data.exe", b"binary", "application/octet-stream")},
    )
    assert response.status_code == 422
