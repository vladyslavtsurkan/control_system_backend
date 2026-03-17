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

    def __init__(self, message: str = MessageException.ORGANIZATION_ACCESS_DENIED) -> None:
        super().__init__(message=message)


class OrganizationPermissionDeniedException(ForbiddenException):
    """Exception raised when a user doesn't have permission to perform an action on an organization."""

    def __init__(self, message: str = MessageException.ORGANIZATION_PERMISSION_DENIED) -> None:
        super().__init__(message=message)


class CannotRemoveOwnerException(ForbiddenException):
    """Exception raised when trying to remove an owner from an organization."""

    def __init__(self, message: str = MessageException.CANNOT_REMOVE_OWNER) -> None:
        super().__init__(message=message)


class AdminCanOnlyRemoveMembersException(ForbiddenException):
    """Exception raised when an admin tries to remove a non-member role."""

    def __init__(self, message: str = MessageException.ADMIN_CAN_ONLY_REMOVE_MEMBERS) -> None:
        super().__init__(message=message)


class OwnerCannotLeaveException(ForbiddenException):
    """Exception raised when an owner tries to leave an organization."""

    def __init__(self, message: str = MessageException.OWNER_CANNOT_LEAVE) -> None:
        super().__init__(message=message)


class CannotChangeOwnRoleException(BadRequestException):
    """Exception raised when a user tries to change their own role."""

    def __init__(self, message: str = MessageException.CANNOT_CHANGE_OWN_ROLE) -> None:
        super().__init__(message=message)


class RoleAlreadyAssignedException(BadRequestException):
    """Exception raised when trying to assign a role the user already has."""

    def __init__(self, message: str = MessageException.ROLE_ALREADY_ASSIGNED) -> None:
        super().__init__(message=message)
