from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, CreatedAtMixin, SoftDeleteMixin

__all__ = ["Organization"]


class Organization(Base, UUIDMixin, CreatedAtMixin, SoftDeleteMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    users = relationship("User", secondary="user_organization_association", backref="organizations", lazy="subquery")
    opc_servers = relationship(
        "OpcServer", back_populates="organization", cascade="all, delete-orphan", lazy="subquery"
    )
