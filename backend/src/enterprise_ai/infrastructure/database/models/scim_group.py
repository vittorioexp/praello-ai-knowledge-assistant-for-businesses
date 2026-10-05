"""SCIM group persistence model."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from enterprise_ai.infrastructure.database.session import Base


class ScimGroupModel(Base):
    __tablename__ = "scim_groups"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    member_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=lambda: datetime.now(UTC), nullable=False)