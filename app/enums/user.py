from app.enums.base import BaseStrEnum

__all__ = ["UserRoleInOrgEnum"]


class UserRoleInOrgEnum(BaseStrEnum):
    """
    Enum representing user roles in an organization.
    """

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
