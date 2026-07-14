"""Document-related value objects."""

from enum import Enum


class DocumentStatus(str, Enum):
    """Document ingestion lifecycle status."""

    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class DocumentType(str, Enum):
    """Supported document formats."""

    PDF = "pdf"
    DOCX = "docx"
    MARKDOWN = "markdown"

    @classmethod
    def from_content_type(cls, content_type: str) -> "DocumentType | None":
        """Resolve document type from MIME type."""
        mapping = {
            "application/pdf": cls.PDF,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": cls.DOCX,
            "text/markdown": cls.MARKDOWN,
            "text/x-markdown": cls.MARKDOWN,
            "text/plain": cls.MARKDOWN,
        }
        return mapping.get(content_type)

    @classmethod
    def from_extension(cls, filename: str) -> "DocumentType | None":
        """Resolve document type from file extension."""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        mapping = {
            "pdf": cls.PDF,
            "docx": cls.DOCX,
            "md": cls.MARKDOWN,
            "markdown": cls.MARKDOWN,
            "txt": cls.MARKDOWN,
        }
        return mapping.get(ext)
