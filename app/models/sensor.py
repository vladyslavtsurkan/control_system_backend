import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, Text, UUID, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import SensorDataTypeEnum
from app.models.base import Base, UUIDMixin, CreatedAtMixin, SoftDeleteMixin, enum_values

__all__ = ["Sensor"]


class Sensor(Base, UUIDMixin, CreatedAtMixin, SoftDeleteMixin):
    __tablename__ = "sensors"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opc_server_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opc_servers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    node_id: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[SensorDataTypeEnum] = mapped_column(
        Enum(SensorDataTypeEnum, values_callable=enum_values), nullable=False, default=SensorDataTypeEnum.numeric
    )
    units: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_writable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    opc_server = relationship("OpcServer", back_populates="sensors", lazy="subquery")
    readings = relationship("Reading", back_populates="sensor", cascade="all, delete-orphan")
    alert_rules = relationship("AlertRule", back_populates="sensor", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="sensor", cascade="all, delete-orphan")
    target_alert_actions = relationship("AlertAction", back_populates="target_sensor", cascade="all, delete-orphan")

    __table_args__ = (
        Index(
            "uq_active_sensor_name",
            "opc_server_id",
            "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "idx_active_sensor_node",
            "opc_server_id",
            "node_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
