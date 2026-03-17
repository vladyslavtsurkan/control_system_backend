import uuid

from sqlalchemy import String, Boolean, ForeignKey, Enum, Index, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.enums import UserRoleInOrgEnum
from app.models.base import Base, UUIDMixin, TimestampMixin

__all__ = ["User", "UserOrganizationAssociation"]


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class UserOrganizationAssociation(Base):
    __tablename__ = "user_organization_association"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
    role: Mapped[UserRoleInOrgEnum] = mapped_column(
        Enum(UserRoleInOrgEnum), nullable=False, default=UserRoleInOrgEnum.MEMBER
    )

    __table_args__ = (Index("idx_org_users_reverse", "organization_id", "user_id"),)
