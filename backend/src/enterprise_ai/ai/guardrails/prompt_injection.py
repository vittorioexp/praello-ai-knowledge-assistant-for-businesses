"""Prompt injection detection for RAG queries."""

import re

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior|above)",
    r"you\s+are\s+now\s+",
    r"system\s*prompt",
    r"reveal\s+(your\s+)?instructions",
    r"jailbreak",
    r"do\s+anything\s+now",
]


class PromptInjectionGuard:
    """Detects potential prompt injection attempts."""

    def __init__(self) -> None:
        self._patterns = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

    def is_safe(self, text: str) -> bool:
        return not any(pattern.search(text) for pattern in self._patterns)

    def sanitize_response(self, text: str) -> str:
        """Strip attempts to leak system instructions from output."""
        lines = [
            line
            for line in text.splitlines()
            if not any(p.search(line) for p in self._patterns)
        ]
        return "\n".join(lines).strip()
