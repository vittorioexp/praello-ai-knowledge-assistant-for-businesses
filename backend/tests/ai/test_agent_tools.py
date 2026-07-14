"""Tests for agent tools."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from enterprise_ai.ai.tools.filesystem import FilesystemSearchTool
from enterprise_ai.ai.tools.sql_search import SQLSearchTool
from enterprise_ai.infrastructure.config.settings import Settings


@pytest.mark.asyncio
async def test_sql_search_allows_select(db_session: AsyncSession) -> None:
    tool = SQLSearchTool(db_session)
    result = await tool.execute(query="SELECT email, full_name FROM users LIMIT 5")
    assert "Error" not in result or "No results" in result


@pytest.mark.asyncio
async def test_sql_search_blocks_insert(db_session: AsyncSession) -> None:
    tool = SQLSearchTool(db_session)
    result = await tool.execute(query="INSERT INTO users VALUES ('x')")
    assert "only SELECT" in result


@pytest.mark.asyncio
async def test_sql_search_blocks_forbidden_tables(db_session: AsyncSession) -> None:
    tool = SQLSearchTool(db_session)
    result = await tool.execute(query="SELECT * FROM secrets")
    assert "not allowed" in result


@pytest.mark.asyncio
async def test_filesystem_search(tmp_path) -> None:
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    (upload_dir / "policy.md").write_text("remote work policy", encoding="utf-8")

    settings = Settings(
        app_env="test",
        app_secret_key="test-secret-key-minimum-32-chars-long",
        jwt_secret_key="test-jwt-secret-key-min-32-chars",
        upload_dir=str(upload_dir),
    )
    tool = FilesystemSearchTool(settings)
    result = await tool.execute(pattern="policy")
    assert "policy.md" in result
