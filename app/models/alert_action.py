import uuid
from typing import Any

from sqlalchemy import ForeignKey, UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, CreatedAtMixin

__all__ = ["AlertAction"]


class AlertAction(Base, UUIDMixin, CreatedAtMixin):
    __tablename__ = "alert_actions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_sensor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trigger_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    resolve_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    rule = relationship("AlertRule", back_populates="actions", lazy="subquery")
    target_sensor = relationship("Sensor", back_populates="target_alert_actions", lazy="subquery")
