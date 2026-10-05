"""Persist connector cursors and synchronization status."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "connector_sync_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("connector_type", sa.String(length=64), nullable=False),
        sa.Column("external_account_id", sa.String(length=512), nullable=False),
        sa.Column("cursor", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="idle"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "connector_type",
            "external_account_id",
            name="uq_connector_sync_identity",
        ),
    )
    op.create_index(
        "ix_connector_sync_states_organization_id",
        "connector_sync_states",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_connector_sync_states_organization_id",
        table_name="connector_sync_states",
    )
    op.drop_table("connector_sync_states")
