from uuid import UUID

from app.core.constants import PAGINATION_PER_PAGE
from app.core.exc import ObjectNotFoundException, OrganizationPermissionDeniedException
from app.enums import UserRoleInOrgEnum
from app.schemas.alert_rule import (
    AlertRuleCreateRequest,
    AlertRuleUpdateRequest,
    AlertRuleResponse,
)
from app.schemas.base import PaginatedResponse
from app.schemas.user import UserResponse
from app.services.base import TenantValidationMixin
from app.uow.sql import SQLUnitOfWork

__all__ = ["AlertRuleService"]


class AlertRuleService(TenantValidationMixin):
    EDIT_ROLES = {UserRoleInOrgEnum.OWNER, UserRoleInOrgEnum.ADMIN}

    async def _check_admin_or_owner(self, uow: SQLUnitOfWork, user_id: UUID, organization_id: UUID) -> None:
        """Check that the user has admin or owner role in the organization."""
        role = await uow.organization.get_user_role_in_organization(user_id=user_id, organization_id=organization_id)
        if role not in self.EDIT_ROLES:
            raise OrganizationPermissionDeniedException

    async def create_alert_rule(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        current_user: UserResponse,
        request: AlertRuleCreateRequest,
    ) -> AlertRuleResponse:
        """Create a new alert rule for a sensor. Only admin/owner."""
        async with uow:
            await self._check_admin_or_owner(uow, current_user.id, tenant_id)
            await self._validate_sensor_tenant(uow, request.sensor_id, tenant_id)
            data = request.model_dump()
            alert_rule = await uow.alert_rule.create(data)
            return AlertRuleResponse.model_validate(alert_rule)

    async def get_alert_rules(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        sensor_id: UUID | None = None,
        offset: int = 0,
        limit: int = PAGINATION_PER_PAGE,
    ) -> PaginatedResponse[AlertRuleResponse]:
        """Get alert rules, optionally filtered by sensor."""
        async with uow:
            if sensor_id:
                await self._validate_sensor_tenant(uow, sensor_id, tenant_id)
                filters = {"sensor_id": sensor_id}
            else:
                tenant_servers, _ = await uow.opc_server.get_multi(
                    is_deleted=False, organization_id=tenant_id, limit=10000
                )
                server_ids = [s.id for s in tenant_servers]
                if not server_ids:
                    return PaginatedResponse(items=[], count=0, per_page=limit)
                tenant_sensors, _ = await uow.sensor.get_multi(opc_server_id__in=server_ids, limit=10000)
                sensor_ids = [s.id for s in tenant_sensors]
                if not sensor_ids:
                    return PaginatedResponse(items=[], count=0, per_page=limit)
                filters = {"sensor_id__in": sensor_ids}

            alert_rules, count = await uow.alert_rule.get_multi(
                offset=offset,
                limit=limit,
                order_by="-id",
                **filters,
            )
            return PaginatedResponse(
                items=[AlertRuleResponse.model_validate(r) for r in alert_rules],
                count=count,
                per_page=limit,
            )

    async def get_alert_rule(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        alert_rule_id: UUID,
    ) -> AlertRuleResponse:
        """Get a specific alert rule by ID."""
        async with uow:
            alert_rule = await uow.alert_rule.get(filters={"id": alert_rule_id})
            if not alert_rule:
                raise ObjectNotFoundException(str(alert_rule_id), "AlertRule")
            await self._validate_sensor_tenant(uow, alert_rule.sensor_id, tenant_id)
            return AlertRuleResponse.model_validate(alert_rule)

    async def update_alert_rule(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        current_user: UserResponse,
        alert_rule_id: UUID,
        request: AlertRuleUpdateRequest,
    ) -> AlertRuleResponse:
        """Update an alert rule. Only admin/owner."""
        async with uow:
            await self._check_admin_or_owner(uow, current_user.id, tenant_id)

            alert_rule = await uow.alert_rule.get(filters={"id": alert_rule_id})
            if not alert_rule:
                raise ObjectNotFoundException(str(alert_rule_id), "AlertRule")
            await self._validate_sensor_tenant(uow, alert_rule.sensor_id, tenant_id)

            updates = request.model_dump(exclude_unset=True)
            updated = await uow.alert_rule.update(
                filters={"id": alert_rule_id},
                updates=updates,
            )
            return AlertRuleResponse.model_validate(updated)

    async def delete_alert_rule(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        current_user: UserResponse,
        alert_rule_id: UUID,
    ) -> None:
        """Delete an alert rule. Only admin/owner."""
        async with uow:
            await self._check_admin_or_owner(uow, current_user.id, tenant_id)

            alert_rule = await uow.alert_rule.get(filters={"id": alert_rule_id})
            if not alert_rule:
                raise ObjectNotFoundException(str(alert_rule_id), "AlertRule")
            await self._validate_sensor_tenant(uow, alert_rule.sensor_id, tenant_id)
            await uow.alert_rule.delete(filters={"id": alert_rule_id})
