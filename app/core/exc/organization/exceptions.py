from app.enums import MessageException
from app.core.exc.base.exceptions import ForbiddenException, BadRequestException

__all__ = [
    "OrganizationAccessDeniedException",
    "OrganizationPermissionDeniedException",
    "CannotRemoveOwnerException",
    "AdminCanOnlyRemoveMembersException",
    "OwnerCannotLeaveException",
    "CannotChangeOwnRoleException",
    "RoleAlreadyAssignedException",
]


class OrganizationAccessDeniedException(ForbiddenException):
    """Exception raised when a user doesn't have access to an organization."""

    def __init__(self, message: str = MessageException.organization_access_denied) -> None:
        super().__init__(message=message)


class OrganizationPermissionDeniedException(ForbiddenException):
    """Exception raised when a user doesn't have permission to perform an action on an organization."""

    def __init__(self, message: str = MessageException.organization_permission_denied) -> None:
        super().__init__(message=message)


class CannotRemoveOwnerException(ForbiddenException):
    """Exception raised when trying to remove an owner from an organization."""

    def __init__(self, message: str = MessageException.cannot_remove_owner) -> None:
        super().__init__(message=message)


class AdminCanOnlyRemoveMembersException(ForbiddenException):
    """Exception raised when an admin tries to remove a non-member role."""

    def __init__(self, message: str = MessageException.admin_can_only_remove_members) -> None:
        super().__init__(message=message)


class OwnerCannotLeaveException(ForbiddenException):
    """Exception raised when an owner tries to leave an organization."""

    def __init__(self, message: str = MessageException.owner_cannot_leave) -> None:
        super().__init__(message=message)


class CannotChangeOwnRoleException(BadRequestException):
    """Exception raised when a user tries to change their own role."""

    def __init__(self, message: str = MessageException.cannot_change_own_role) -> None:
        super().__init__(message=message)


class RoleAlreadyAssignedException(BadRequestException):
    """Exception raised when trying to assign a role the user already has."""

    def __init__(self, message: str = MessageException.role_already_assigned) -> None:
        super().__init__(message=message)
