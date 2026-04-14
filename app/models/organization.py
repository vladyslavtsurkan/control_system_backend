from sqlalchemy import Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, CreatedAtMixin, SoftDeleteMixin

__all__ = ["Organization"]


class Organization(Base, UUIDMixin, CreatedAtMixin, SoftDeleteMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    users = relationship("User", secondary="user_organization_association", backref="organizations", lazy="subquery")
    opc_servers = relationship(
        "OpcServer", back_populates="organization", cascade="all, delete-orphan", lazy="subquery"
    )

    __table_args__ = (
        Index(
            "idx_organizations_active",
            "id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
