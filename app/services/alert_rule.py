from uuid import UUID

from app.core.constants import PAGINATION_PER_PAGE
from app.core.exc import ObjectNotFoundException, BadRequestException
from app.enums import AlertConditionEnum, SensorDataTypeEnum
from app.enums.audit_log import AuditActionEnum, AuditResourceTypeEnum
from app.schemas.alert_rule import (
    AlertActionCreateRequest,
    AlertRuleCreateRequest,
    AlertRuleUpdateRequest,
    AlertRuleResponse,
)
from app.schemas.base import PaginatedResponse
from app.schemas.user import UserResponse
from app.services.audit_log import AuditLogService
from app.services.mixins import TenantValidationMixin
from app.uow.redis import RedisUnitOfWork
from app.uow.rabbitmq import RabbitMQUnitOfWork
from app.uow.sql import SQLUnitOfWork

__all__ = ["AlertRuleService"]


class AlertRuleService(TenantValidationMixin):
    @staticmethod
    def _validate_condition_for_sensor_type(condition: AlertConditionEnum, data_type: SensorDataTypeEnum) -> None:
        if condition == AlertConditionEnum.no_data:
            return
        if data_type == SensorDataTypeEnum.numeric:
            return
        if condition in {AlertConditionEnum.equals, AlertConditionEnum.not_equals}:
            return
        raise BadRequestException("Only equals, not_equals and no_data conditions are allowed for non-numeric sensors")

    async def _build_alert_action_rows(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        action_requests: list[AlertActionCreateRequest],
    ) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for action in action_requests:
            target_sensor = await self._get_active_sensor_for_tenant(
                uow=uow,
                sensor_id=action.target_sensor_id,
                tenant_id=tenant_id,
            )
            if not target_sensor:
                raise ObjectNotFoundException(str(action.target_sensor_id), "Sensor")
            if not target_sensor.is_writable:
                raise BadRequestException("Target sensor is not writable")
            rows.append({**action.model_dump(), "organization_id": tenant_id})
        return rows

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
            sensor = await self._get_active_sensor_for_tenant(uow, request.sensor_id, tenant_id)
            if not sensor:
                raise ObjectNotFoundException(str(request.sensor_id), "Sensor")
            self._validate_condition_for_sensor_type(request.condition, sensor.data_type)
            action_rows = await self._build_alert_action_rows(uow, tenant_id, request.actions or [])
            data = request.model_dump(exclude={"actions"})
            data["organization_id"] = tenant_id
            alert_rule = await uow.alert_rule.create(data)
            if action_rows:
                await uow.alert_action.create_many(
                    [{"rule_id": alert_rule.id, **action_row} for action_row in action_rows]
                )
            created_alert_rule_id = alert_rule.id
            alert_rule_full = await uow.alert_rule.get_for_tenant_by_id(created_alert_rule_id, tenant_id)
            result = AlertRuleResponse.model_validate(alert_rule_full or alert_rule)
            await AuditLogService.log(
                uow=uow,
                organization_id=tenant_id,
                actor=current_user,
                action=AuditActionEnum.created,
                resource_type=AuditResourceTypeEnum.alert_rule,
                resource_id=created_alert_rule_id,
                resource_name=alert_rule.name,
                metadata={"sensor_id": str(request.sensor_id)},
            )

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

    @staticmethod
    async def get_alert_rule(
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

            sensor = await self._get_active_sensor_for_tenant(uow, alert_rule.sensor_id, tenant_id)
            if not sensor:
                raise ObjectNotFoundException(str(alert_rule.sensor_id), "Sensor")

            updates = request.model_dump(exclude_unset=True)
            new_condition = updates.get("condition", alert_rule.condition)
            self._validate_condition_for_sensor_type(new_condition, sensor.data_type)
            actions_provided = "actions" in updates
            updates.pop("actions", None)

            if updates:
                await uow.alert_rule.update(
                    filters={"id": alert_rule_id},
                    updates=updates,
                )

            if actions_provided:
                action_rows = await self._build_alert_action_rows(uow, tenant_id, request.actions or [])
                await uow.alert_action.delete_many(filters={"rule_id": alert_rule_id})
                if action_rows:
                    await uow.alert_action.create_many(
                        [{"rule_id": alert_rule_id, **action_row} for action_row in action_rows]
                    )

            refreshed = await uow.alert_rule.get_for_tenant_by_id(alert_rule_id=alert_rule_id, tenant_id=tenant_id)
            if not refreshed:
                raise ObjectNotFoundException(str(alert_rule_id), "AlertRule")
            result = AlertRuleResponse.model_validate(refreshed)
            await AuditLogService.log(
                uow=uow,
                organization_id=tenant_id,
                actor=current_user,
                action=AuditActionEnum.updated,
                resource_type=AuditResourceTypeEnum.alert_rule,
                resource_id=alert_rule_id,
                resource_name=alert_rule.name,
                metadata={"updates": {k: v for k, v in updates.items()}},
            )

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
            await AuditLogService.log(
                uow=uow,
                organization_id=tenant_id,
                actor=current_user,
                action=AuditActionEnum.deleted,
                resource_type=AuditResourceTypeEnum.alert_rule,
                resource_id=alert_rule_id,
                resource_name=alert_rule.name,
            )

        async with RedisUnitOfWork() as redis_uow:
            await redis_uow.alert_state.clear_by_rule(alert_rule_id)
        async with RabbitMQUnitOfWork() as rmq:
            await rmq.control.publish_rule_invalidation()
