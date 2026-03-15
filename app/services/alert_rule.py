from uuid import UUID

from app.core.constants import PAGINATION_PER_PAGE
from app.core.exc import ObjectNotFoundException
from app.schemas.alert_rule import (
    AlertRuleCreateRequest,
    AlertRuleUpdateRequest,
    AlertRuleResponse,
)
from app.schemas.base import PaginatedResponse
from app.schemas.user import UserResponse
from app.services.mixins import TenantValidationMixin
from app.uow.redis import RedisUnitOfWork
from app.uow.rabbitmq import RabbitMQUnitOfWork
from app.uow.sql import SQLUnitOfWork

__all__ = ["AlertRuleService"]


class AlertRuleService(TenantValidationMixin):
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
            created_alert_rule_id = alert_rule.id
            result = AlertRuleResponse.model_validate(alert_rule)

        async with RedisUnitOfWork() as redis_uow:
            await redis_uow.alert_state.clear_by_rule(created_alert_rule_id)
        async with RabbitMQUnitOfWork() as rmq:
            await rmq.control.publish_rule_invalidation()
        return result

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
            await self._validate_active_organization(uow, tenant_id)

            alert_rules, count = await uow.alert_rule.get_multi_for_tenant(
                tenant_id=tenant_id,
                offset=offset,
                limit=limit,
                sensor_id=sensor_id,
                order_by="-id",
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
            alert_rule = await uow.alert_rule.get_for_tenant_by_id(alert_rule_id=alert_rule_id, tenant_id=tenant_id)
            if not alert_rule:
                raise ObjectNotFoundException(str(alert_rule_id), "AlertRule")
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

            alert_rule = await uow.alert_rule.get_for_tenant_by_id(alert_rule_id=alert_rule_id, tenant_id=tenant_id)
            if not alert_rule:
                raise ObjectNotFoundException(str(alert_rule_id), "AlertRule")

            updates = request.model_dump(exclude_unset=True)
            updated = await uow.alert_rule.update(
                filters={"id": alert_rule_id},
                updates=updates,
            )
            result = AlertRuleResponse.model_validate(updated)

        async with RedisUnitOfWork() as redis_uow:
            await redis_uow.alert_state.clear_by_rule(alert_rule_id)
        async with RabbitMQUnitOfWork() as rmq:
            await rmq.control.publish_rule_invalidation()
        return result

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

            alert_rule = await uow.alert_rule.get_for_tenant_by_id(alert_rule_id=alert_rule_id, tenant_id=tenant_id)
            if not alert_rule:
                raise ObjectNotFoundException(str(alert_rule_id), "AlertRule")
            await uow.alert_rule.delete(filters={"id": alert_rule_id})

        async with RedisUnitOfWork() as redis_uow:
            await redis_uow.alert_state.clear_by_rule(alert_rule_id)
        async with RabbitMQUnitOfWork() as rmq:
            await rmq.control.publish_rule_invalidation()
