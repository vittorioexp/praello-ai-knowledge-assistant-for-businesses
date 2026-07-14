"""Filesystem search tool."""

from pathlib import Path

from enterprise_ai.ai.tools.base import AgentTool
from enterprise_ai.domain.value_objects.agent import ToolRiskLevel
from enterprise_ai.infrastructure.config.settings import Settings


class FilesystemSearchTool(AgentTool):
    """Search files in the approved upload directory."""

    name = "filesystem_search"
    description = "Search for files by name or content in the document upload area."
    risk_level = ToolRiskLevel.LOW
    requires_approval = False

    def __init__(self, settings: Settings) -> None:
        self._base = Path(settings.upload_dir)

    async def execute(self, *, pattern: str = "", **kwargs) -> str:
        if not self._base.exists():
            return "Upload directory is empty"

        matches: list[str] = []
        for path in self._base.rglob("*"):
            if not path.is_file():
                continue
            if pattern and pattern.lower() not in path.name.lower():
                try:
                    if pattern.lower() not in path.read_text(encoding="utf-8", errors="ignore").lower():
                        continue
                except OSError:
                    continue
            matches.append(str(path.relative_to(self._base)))
            if len(matches) >= 20:
                break

        return "\n".join(matches) if matches else f"No files matching '{pattern}'"
