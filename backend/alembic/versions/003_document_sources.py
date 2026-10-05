"""Add source identity and version fields to documents."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("source_type", sa.String(length=32), nullable=False, server_default="upload"),
    )
    op.add_column("documents", sa.Column("source_id", sa.String(length=512), nullable=True))
    op.add_column(
        "documents", sa.Column("source_item_id", sa.String(length=1024), nullable=True)
    )
    op.add_column(
        "documents", sa.Column("source_version", sa.String(length=512), nullable=True)
    )
    op.create_index(
        "ix_documents_source_identity",
        "documents",
        ["source_type", "source_id", "source_item_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_documents_source_identity", table_name="documents")
    op.drop_column("documents", "source_version")
    op.drop_column("documents", "source_item_id")
    op.drop_column("documents", "source_id")
    op.drop_column("documents", "source_type")