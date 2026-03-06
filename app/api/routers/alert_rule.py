from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.dependencies import (
    TenantUnitOfWorkDep,
    TenantIdDep,
    current_user,
    offset_query,
    limit_query,
    alert_rule_service,
)
from app.schemas.alert_rule import (
    AlertRuleCreateRequest,
    AlertRuleUpdateRequest,
    AlertRuleResponse,
)
from app.schemas.base import PaginatedResponse

__all__ = ["router"]

router = APIRouter(prefix="/alert-rules", tags=["Alert Rules"])


@router.post("/", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    uow: TenantUnitOfWorkDep,
    tenant_id: TenantIdDep,
    user: current_user,
    request: AlertRuleCreateRequest,
    service: alert_rule_service,
):
    """
    Create a new alert rule for a sensor.

    Requires X-Tenant-ID header. Only admin/owner.
    """
    return await service.create_alert_rule(uow=uow, tenant_id=tenant_id, current_user=user, request=request)


@router.get("/", response_model=PaginatedResponse[AlertRuleResponse], status_code=status.HTTP_200_OK)
async def get_alert_rules(
    uow: TenantUnitOfWorkDep,
    tenant_id: TenantIdDep,
    service: alert_rule_service,
    sensor_id: UUID | None = Query(None, description="Filter by sensor ID"),
    offset: int = offset_query,
    limit: int = limit_query,
):
    """
    Get alert rules for the current tenant.

    Requires X-Tenant-ID header.
    Optionally filter by sensor ID.
    """
    return await service.get_alert_rules(uow=uow, tenant_id=tenant_id, sensor_id=sensor_id, offset=offset, limit=limit)


@router.get("/{alert_rule_id}", response_model=AlertRuleResponse, status_code=status.HTTP_200_OK)
async def get_alert_rule(
    uow: TenantUnitOfWorkDep,
    tenant_id: TenantIdDep,
    alert_rule_id: UUID,
    service: alert_rule_service,
):
    """
    Get a specific alert rule by ID.

    Requires X-Tenant-ID header.
    """
    return await service.get_alert_rule(uow=uow, tenant_id=tenant_id, alert_rule_id=alert_rule_id)


@router.patch("/{alert_rule_id}", response_model=AlertRuleResponse, status_code=status.HTTP_200_OK)
async def update_alert_rule(
    uow: TenantUnitOfWorkDep,
    tenant_id: TenantIdDep,
    user: current_user,
    alert_rule_id: UUID,
    request: AlertRuleUpdateRequest,
    service: alert_rule_service,
):
    """
    Update an alert rule.

    Requires X-Tenant-ID header. Only admin/owner.
    """
    return await service.update_alert_rule(
        uow=uow, tenant_id=tenant_id, current_user=user, alert_rule_id=alert_rule_id, request=request
    )


@router.delete("/{alert_rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_rule(
    uow: TenantUnitOfWorkDep,
    tenant_id: TenantIdDep,
    user: current_user,
    alert_rule_id: UUID,
    service: alert_rule_service,
):
    """
    Delete an alert rule.

    Requires X-Tenant-ID header. Only admin/owner.
    """
    await service.delete_alert_rule(uow=uow, tenant_id=tenant_id, current_user=user, alert_rule_id=alert_rule_id)
