from datetime import datetime
from enum import Enum as PyEnum
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid7

from sqlalchemy import Boolean, DateTime, String, func, text, ForeignKey
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

__all__ = [
    "Base",
    "UUIDMixin",
    "CreatedAtMixin",
    "UpdatedAtMixin",
    "TimestampMixin",
    "SoftDeleteMixin",
    "TenantMixin",
    "enum_values",
]


def enum_values(enum_cls: type[PyEnum]) -> list[str]:
    """Return enum values for SQLAlchemy Enum(values_callable=...)."""
    return [str(member.value) for member in enum_cls]


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(default=func.now(), server_default=func.now())


class UpdatedAtMixin:
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())


class TimestampMixin(CreatedAtMixin, UpdatedAtMixin):
    """Model with created_at and updated_at fields"""


class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class UUIDMixin:
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid7,
        server_default=text("uuidv7()"),
    )


class TenantMixin:
    """Mixin for models that belong to a specific organization (tenant).

    This mixin adds an organization_id column and is used in conjunction
    with PostgreSQL Row-Level Security (RLS) policies.
    """

    organization_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


class Base(DeclarativeBase):
    type_annotation_map = {
        UUID: postgresql.UUID,
        dict[str, Any]: postgresql.JSONB,
        list[dict[str, Any]]: postgresql.ARRAY(postgresql.JSON),
        list[str]: postgresql.ARRAY(String),
        Decimal: postgresql.NUMERIC(10, 2),
        datetime: DateTime(timezone=True),
        bool: Boolean,
    }
