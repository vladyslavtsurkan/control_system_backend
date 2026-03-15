from uuid import UUID

from app.core.exc import (
    TenantIdRequiredException,
    InvalidTenantIdFormatException,
    TenantAccessDeniedException,
    ObjectNotFoundException,
)
from app.schemas.user import UserResponse
from app.uow.sql import SQLUnitOfWork

__all__ = ["TenantService"]


class TenantService:
    @staticmethod
    async def validate_and_get_tenant_id(
        x_tenant_id: str | None,
        user: UserResponse,
    ) -> UUID:
        """Validate tenant ID from header and check user access.

        Args:
            x_tenant_id: The tenant ID from the request header.
            user: The authenticated user.

        Returns:
            The validated tenant UUID.

        Raises:
            TenantIdRequiredException: If header is missing.
            InvalidTenantIdFormatException: If UUID format is invalid.
            TenantAccessDeniedException: If user doesn't have access to the tenant.
        """
        if not x_tenant_id:
            raise TenantIdRequiredException()

        try:
            tenant_id = UUID(x_tenant_id)
        except ValueError:
            raise InvalidTenantIdFormatException()

        # Validate user has access to this tenant
        async with SQLUnitOfWork() as uow:
            user_role, is_active_org = await uow.organization.get_user_role_and_org_state(
                user_id=user.id,
                organization_id=tenant_id,
            )
            if not user_role:
                raise TenantAccessDeniedException()

            if not is_active_org:
                raise ObjectNotFoundException(str(tenant_id), "Organization")

        return tenant_id
