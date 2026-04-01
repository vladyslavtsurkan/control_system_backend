import datetime
import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, Text, UUID, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, CreatedAtMixin, UpdatedAtMixin

__all__ = ["Alert"]


class Alert(Base, UUIDMixin, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "alerts"

    sensor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False
    )
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alert_rules.id", ondelete="SET NULL"), nullable=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    triggered_value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)

    sensor = relationship("Sensor", back_populates="alerts", lazy="subquery")
    rule = relationship("AlertRule", back_populates="alerts", lazy="subquery")

    __table_args__ = (
        Index("idx_alerts_sensor_id_desc", "sensor_id", "id"),
        Index(
            "uq_active_alert_per_rule",
            "sensor_id",
            "rule_id",
            unique=True,
            postgresql_where=text("resolved_at IS NULL AND rule_id IS NOT NULL"),
        ),
        Index(
            "idx_active_alerts",
            "sensor_id",
            postgresql_where=text("resolved_at IS NULL"),
        ),
    )
