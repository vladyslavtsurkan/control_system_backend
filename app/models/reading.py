import datetime
import uuid
from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, Text, UUID, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

__all__ = ["Reading"]


class Reading(Base):
    __tablename__ = "readings"

    time: Mapped[datetime.datetime] = mapped_column(primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    sensor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False, primary_key=True
    )
    val_num: Mapped[float | None] = mapped_column(Float, nullable=True)
    val_bool: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    val_str: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    sensor = relationship("Sensor", back_populates="readings", lazy="subquery")

    __table_args__ = (
        Index("idx_readings_sensor_time_desc", "sensor_id", "time"),
        {
            "timescaledb_hypertable": {"time_column_name": "time", "chunk_time_interval": "1 day"},
        },
    )
