from sqlalchemy import String, Text, Enum, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import SecurityPolicyEnum, AuthMethodEnum
from app.models.base import Base, UUIDMixin, CreatedAtMixin, SoftDeleteMixin, TenantMixin, enum_values

__all__ = ["OpcServer"]


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
    api_keys = relationship("CollectorApiKey", back_populates="opc_server", uselist=True, cascade="all, delete-orphan")

    __table_args__ = (
        Index(
            "uq_active_opc_server_name",
            "organization_id",
            "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
