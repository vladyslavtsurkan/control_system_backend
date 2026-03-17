from app.enums.base import BaseStrEnum

__all__ = ["UserRoleInOrgEnum"]


class UserRoleInOrgEnum(BaseStrEnum):
    """
    Enum representing user roles in an organization.
    """

    owner = "owner"
    admin = "admin"
    member = "member"
