import uuid

from sqlalchemy import String, Boolean, ForeignKey, Enum, UniqueConstraint, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.enums import UserRoleInOrgEnum
from app.models.base import Base, UUIDMixin, TimestampMixin

__all__ = ["User", "UserOrganizationAssociation"]


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class UserOrganizationAssociation(Base, UUIDMixin):
    __tablename__ = "user_organization_association"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[UserRoleInOrgEnum] = mapped_column(
        Enum(UserRoleInOrgEnum), nullable=False, default=UserRoleInOrgEnum.MEMBER
    )

    __table_args__ = (UniqueConstraint("user_id", "organization_id", name="uq_user_organization_association"),)
