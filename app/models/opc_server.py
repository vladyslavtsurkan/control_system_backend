import datetime
import uuid

from sqlalchemy import String, Text, ForeignKey, UUID, Enum, UniqueConstraint, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import SecurityPolicyEnum, AuthMethodEnum
from app.models.base import Base, UUIDMixin, CreatedAtMixin, SoftDeleteMixin

__all__ = ["OpcServer", "Sensor", "Reading", "Alert"]


class OpcServer(Base, UUIDMixin, CreatedAtMixin, SoftDeleteMixin):
    __tablename__ = "opc_servers"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(512), nullable=False)

    security_policy: Mapped[SecurityPolicyEnum] = mapped_column(
        Enum(SecurityPolicyEnum), nullable=False, default=SecurityPolicyEnum.NONE
    )
    authentication_method: Mapped[AuthMethodEnum] = mapped_column(
        Enum(AuthMethodEnum), nullable=False, default=AuthMethodEnum.ANONYMOUS
    )
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    encrypted_password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    organization = relationship("Organization", back_populates="opc_servers", lazy="subquery")
    sensors = relationship("Sensor", back_populates="opc_server", cascade="all, delete-orphan", lazy="subquery")

    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_opc_server_organization_name"),)


class Sensor(Base, UUIDMixin, CreatedAtMixin, SoftDeleteMixin):
    __tablename__ = "sensors"

    opc_server_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opc_servers.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    node_id: Mapped[str] = mapped_column(String(255), nullable=False)
    units: Mapped[str | None] = mapped_column(String(50), nullable=True)

    opc_server = relationship("OpcServer", back_populates="sensors", lazy="subquery")
    readings = relationship("Reading", back_populates="sensor", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="sensor", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("opc_server_id", "name", name="uq_sensor_opc_server_name"),)


class Reading(Base):
    __tablename__ = "readings"

    time: Mapped[datetime.datetime] = mapped_column(primary_key=True)
    sensor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False, primary_key=True
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)

    sensor = relationship("Sensor", back_populates="readings", lazy="subquery")

    __table_args__ = (
        {
            "timescaledb_hypertable": {"time_column_name": "time", "chunk_time_interval": "1 day"},
        },
    )


class Alert(Base, UUIDMixin, CreatedAtMixin):
    __tablename__ = "alerts"

    sensor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    triggered_value: Mapped[float] = mapped_column(Float, nullable=False)

    sensor = relationship("Sensor", back_populates="alerts", lazy="subquery")
