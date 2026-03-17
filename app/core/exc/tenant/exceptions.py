from app.enums import MessageException
from app.core.exc.base.exceptions import BadRequestException, ForbiddenException

__all__ = [
    "TenantIdRequiredException",
    "InvalidTenantIdFormatException",
    "TenantAccessDeniedException",
]


class TenantIdRequiredException(BadRequestException):
    """Exception raised when X-Tenant-ID header is missing."""

    def __init__(self, message: str = MessageException.TENANT_ID_REQUIRED) -> None:
        super().__init__(message=message)


class InvalidTenantIdFormatException(BadRequestException):
    """Exception raised when X-Tenant-ID header has invalid UUID format."""

    def __init__(self, message: str = MessageException.INVALID_TENANT_ID_FORMAT) -> None:
        super().__init__(message=message)


class TenantAccessDeniedException(ForbiddenException):
    """Exception raised when user doesn't have access to the specified tenant."""

    def __init__(self, message: str = MessageException.TENANT_ACCESS_DENIED) -> None:
        super().__init__(message=message)
