import uuid
from typing import Any

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Integer, String, UUID, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import AlertSeverityEnum, AlertConditionEnum
from app.models.base import Base, UUIDMixin, CreatedAtMixin, enum_values

__all__ = ["AlertRule"]


class AlertRule(Base, UUIDMixin, CreatedAtMixin):
    __tablename__ = "alert_rules"

    sensor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[AlertSeverityEnum] = mapped_column(
        Enum(AlertSeverityEnum, values_callable=enum_values), nullable=False, default=AlertSeverityEnum.warning
    )
    condition: Mapped[AlertConditionEnum] = mapped_column(
        Enum(AlertConditionEnum, values_callable=enum_values), nullable=False
    )
    threshold: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    sensor = relationship("Sensor", back_populates="alert_rules", lazy="subquery")
    alerts = relationship("Alert", back_populates="rule", lazy="subquery")
    actions = relationship("AlertAction", back_populates="rule", cascade="all, delete-orphan", lazy="subquery")

    __table_args__ = (
        Index(
            "idx_active_alert_rules",
            "sensor_id",
            postgresql_where=text("is_active IS TRUE"),
        ),
    )
