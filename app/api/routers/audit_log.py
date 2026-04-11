from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.dependencies import (
    TenantUnitOfWorkDep,
    TenantIdDep,
    current_user,
    offset_query,
    limit_query_default,
    audit_log_service,
)
from app.enums.audit_log import AuditActionEnum, AuditResourceTypeEnum
from app.schemas.audit_log import AuditLogResponse
from app.schemas.base import PaginatedResponse

__all__ = ["router"]

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("/", response_model=PaginatedResponse[AuditLogResponse], status_code=status.HTTP_200_OK)
async def get_audit_logs(
    uow: TenantUnitOfWorkDep,
    tenant_id: TenantIdDep,
    user: current_user,
    service: audit_log_service,
    resource_type: AuditResourceTypeEnum | None = Query(None, description="Filter by resource type"),
    action: AuditActionEnum | None = Query(None, description="Filter by action"),
    actor_id: UUID | None = Query(None, description="Filter by actor (user) ID"),
    offset: int = offset_query,
    limit: int = limit_query_default,
):
    """
    Get paginated audit log entries for the current tenant.

    Requires X-Tenant-ID header. Only accessible to admin/owner.
    """
    return await service.get_audit_logs(
        uow=uow,
        tenant_id=tenant_id,
        current_user=user,
        resource_type=resource_type,
        action=action,
        actor_id=actor_id,
        offset=offset,
        limit=limit,
    )
