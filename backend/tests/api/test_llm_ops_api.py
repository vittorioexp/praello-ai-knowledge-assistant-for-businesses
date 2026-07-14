"""Tests for LLM ops API."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_llm_usage_requires_admin(client: AsyncClient, contributor_token: str) -> None:
    response = await client.get(
        "/api/v1/llm/usage",
        headers={"Authorization": f"Bearer {contributor_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_llm_usage_returns_summary(client: AsyncClient, admin_token: str) -> None:
    response = await client.get(
        "/api/v1/llm/usage",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_requests" in data
    assert "total_cost_usd" in data
