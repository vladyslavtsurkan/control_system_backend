import uuid
from typing import Any

from sqlalchemy import Enum, ForeignKey, String, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.enums.audit_log import AuditActionEnum, AuditResourceTypeEnum
from app.models.base import Base, UUIDMixin, CreatedAtMixin, TenantMixin, enum_values

__all__ = ["AuditLog"]


class AuditLog(Base, UUIDMixin, CreatedAtMixin, TenantMixin):
    """Immutable append-only record of every mutating action within an organization."""

    __tablename__ = "audit_logs"

    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False)

    action: Mapped[AuditActionEnum] = mapped_column(
        Enum(AuditActionEnum, values_callable=enum_values, name="auditactionenum"),
        nullable=False,
        index=True,
    )
    resource_type: Mapped[AuditResourceTypeEnum] = mapped_column(
        Enum(AuditResourceTypeEnum, values_callable=enum_values, name="auditresourcetypeenum"),
        nullable=False,
        index=True,
    )
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    resource_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(nullable=True)
