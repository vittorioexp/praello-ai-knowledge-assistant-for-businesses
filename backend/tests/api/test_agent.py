"""Tests for agent API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_agent_conversation(client: AsyncClient, analyst_token: str) -> None:
    response = await client.post(
        "/api/v1/agent/conversations",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"message": "Hello, what can you help with?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "thread_id" in data
    assert "answer" in data
    assert "status" in data


@pytest.mark.asyncio
async def test_agent_requires_execute_permission(
    client: AsyncClient,
    contributor_token: str,
) -> None:
    response = await client.post(
        "/api/v1/agent/conversations",
        headers={"Authorization": f"Bearer {contributor_token}"},
        json={"message": "Hello"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_agent_approval_flow(client: AsyncClient, analyst_token: str) -> None:
    send_resp = await client.post(
        "/api/v1/agent/conversations",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"message": "Send a slack message to the team"},
    )
    assert send_resp.status_code == 200
    data = send_resp.json()
    thread_id = data["thread_id"]

    if data.get("requires_approval"):
        approve_resp = await client.post(
            f"/api/v1/agent/conversations/{thread_id}/approve",
            headers={"Authorization": f"Bearer {analyst_token}"},
            json={"approved": True},
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] in ("completed", "running")


@pytest.mark.asyncio
async def test_get_conversation(client: AsyncClient, analyst_token: str) -> None:
    send_resp = await client.post(
        "/api/v1/agent/conversations",
        headers={"Authorization": f"Bearer {analyst_token}"},
        json={"message": "Hello"},
    )
    thread_id = send_resp.json()["thread_id"]

    get_resp = await client.get(
        f"/api/v1/agent/conversations/{thread_id}",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["thread_id"] == thread_id
