import datetime
import uuid
from typing import Any

from sqlalchemy import String, Text, ForeignKey, UUID, Enum, Index, Boolean, Float, Integer, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import SecurityPolicyEnum, AuthMethodEnum, AlertSeverityEnum, AlertConditionEnum, SensorDataTypeEnum
from app.models.base import Base, UUIDMixin, CreatedAtMixin, UpdatedAtMixin, SoftDeleteMixin, TenantMixin, enum_values

__all__ = ["OpcServer", "Sensor", "Reading", "AlertRule", "Alert", "CollectorApiKey"]


class OpcServer(Base, UUIDMixin, CreatedAtMixin, SoftDeleteMixin, TenantMixin):
    __tablename__ = "opc_servers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(512), nullable=False)

    security_policy: Mapped[SecurityPolicyEnum] = mapped_column(
        Enum(SecurityPolicyEnum, values_callable=enum_values), nullable=False, default=SecurityPolicyEnum.none
    )
    authentication_method: Mapped[AuthMethodEnum] = mapped_column(
        Enum(AuthMethodEnum, values_callable=enum_values), nullable=False, default=AuthMethodEnum.anonymous
    )
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    encrypted_password: Mapped[str | None] = mapped_column(String(512), nullable=True)

    organization = relationship("Organization", back_populates="opc_servers", lazy="subquery")
    sensors = relationship("Sensor", back_populates="opc_server", cascade="all, delete-orphan", lazy="subquery")
    api_key = relationship("CollectorApiKey", back_populates="opc_server", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index(
            "uq_active_opc_server_name",
            "organization_id",
            "name",
            unique=True,
            postgresql_where=text("NOT is_deleted"),
        ),
    )


class Sensor(Base, UUIDMixin, CreatedAtMixin, SoftDeleteMixin):
    __tablename__ = "sensors"

    opc_server_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opc_servers.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    node_id: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[SensorDataTypeEnum] = mapped_column(
        Enum(SensorDataTypeEnum, values_callable=enum_values), nullable=False, default=SensorDataTypeEnum.numeric
    )
    units: Mapped[str | None] = mapped_column(String(50), nullable=True)

    opc_server = relationship("OpcServer", back_populates="sensors", lazy="subquery")
    readings = relationship("Reading", back_populates="sensor", cascade="all, delete-orphan")
    alert_rules = relationship("AlertRule", back_populates="sensor", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="sensor", cascade="all, delete-orphan")

    __table_args__ = (
        Index(
            "uq_active_sensor_name",
            "opc_server_id",
            "name",
            unique=True,
            postgresql_where=text("NOT is_deleted"),
        ),
        Index(
            "idx_active_sensor_node",
            "opc_server_id",
            "node_id",
            postgresql_where=text("NOT is_deleted"),
        ),
    )


class Reading(Base):
    __tablename__ = "readings"

    time: Mapped[datetime.datetime] = mapped_column(primary_key=True)
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

    __table_args__ = (
        Index(
            "idx_active_alert_rules",
            "sensor_id",
            postgresql_where=text("is_active IS TRUE"),
        ),
    )


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


class CollectorApiKey(Base, UUIDMixin, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "collector_api_keys"

    opc_server_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opc_servers.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    hashed_key: Mapped[str] = mapped_column(String(255), nullable=False)
    last_used_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)

    opc_server = relationship("OpcServer", back_populates="api_key", lazy="subquery")
