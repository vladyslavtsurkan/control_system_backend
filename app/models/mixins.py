import uuid

from sqlalchemy import UUID, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

__all__ = ["TenantMixin"]


class TenantMixin:
    """Mixin for models that belong to a specific organization (tenant).

    This mixin adds an organization_id column and is used in conjunction
    with PostgreSQL Row-Level Security (RLS) policies.
    """

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
