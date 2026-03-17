from uuid import UUID

from app.core.exc import ObjectNotFoundException, OrganizationPermissionDeniedException
from app.enums import UserRoleInOrgEnum
from app.uow.sql import SQLUnitOfWork

__all__ = ["TenantValidationMixin"]

EDIT_ROLES = {UserRoleInOrgEnum.owner, UserRoleInOrgEnum.admin}


class TenantValidationMixin:
    """Mixin providing common tenant-scoped validation helpers."""

    @staticmethod
    async def _is_active_organization(uow: SQLUnitOfWork, organization_id: UUID) -> bool:
        organization = await uow.organization.get(filters={"id": organization_id, "is_deleted": False})
        return organization is not None

    @staticmethod
    async def _validate_active_organization(uow: SQLUnitOfWork, organization_id: UUID) -> None:
        if not await TenantValidationMixin._is_active_organization(uow, organization_id):
            raise ObjectNotFoundException(str(organization_id), "Organization")

    @staticmethod
    async def _check_admin_or_owner(uow: SQLUnitOfWork, user_id: UUID, organization_id: UUID) -> None:
        """Check that the user has admin or owner role in the organization."""
        role, is_active_org = await uow.organization.get_user_role_and_org_state(user_id, organization_id)
        if not is_active_org:
            raise ObjectNotFoundException(str(organization_id), "Organization")
        if role not in EDIT_ROLES:
            raise OrganizationPermissionDeniedException

    @staticmethod
    async def _get_active_sensor_for_tenant(uow: SQLUnitOfWork, sensor_id: UUID, tenant_id: UUID):
        return await uow.sensor.get_active_for_tenant(sensor_id=sensor_id, tenant_id=tenant_id)

    @staticmethod
    async def _validate_sensor_tenant(uow: SQLUnitOfWork, sensor_id: UUID, tenant_id: UUID) -> None:
        """Validate that a sensor belongs to the given tenant via its OPC server."""
        sensor = await TenantValidationMixin._get_active_sensor_for_tenant(uow, sensor_id, tenant_id)
        if not sensor:
            raise ObjectNotFoundException(str(sensor_id), "Sensor")
