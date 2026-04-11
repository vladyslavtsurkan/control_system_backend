from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Query, Header, WebSocket, HTTPException, status

from app.api.ws.manager import ConnectionManager
from app.core.constants import (
    PAGINATION_PER_PAGE,
    PAGINATION_MAX_PER_PAGE,
    PAGINATION_DEFAULT_OFFSET,
    READINGS_DEFAULT_RANGE_HOURS,
    READINGS_DEFAULT_BUCKET_INTERVAL,
    READINGS_ALLOWED_BUCKET_INTERVALS,
    SENSOR_PREFETCH_DEFAULT_WINDOW_MINUTES,
    SENSOR_PREFETCH_MAX_WINDOW_MINUTES,
    READINGS_MAX_HOURS_WINDOW,
)
from app.schemas import UserResponse
from app.services import (
    AlertRuleService,
    AuditLogService,
    AuthService,
    CollectorService,
    UserService,
    OrganizationService,
    OpcServerService,
    SensorService,
    ReadingService,
    AlertService,
    TenantService,
    WsAuthService,
)
from app.uow.sql import SQLUnitOfWork

__all__ = [
    "SQLUnitOfWorkDep",
    "user_service",
    "auth_service",
    "current_user",
    "collector_service",
    "organization_service",
    "opc_server_service",
    "sensor_service",
    "reading_service",
    "alert_service",
    "alert_rule_service",
    "audit_log_service",
    "ws_auth_service",
    "offset_query",
    "limit_query_default",
    "limit_query_factory",
    "bucket_interval_query",
    "prefetch_window_minutes_query",
    "get_readings_range",
    "get_tenant_id",
    "get_tenant_uow",
    "ws_authenticate",
    "TenantUnitOfWorkDep",
    "AdminUnitOfWorkDep",
    "TenantIdDep",
    "ConnectionManagerDep",
    "ws_authenticate_dep",
    "ReadingsRangeDep",
    "BucketIntervalDep",
]

from app.utils.helpers import ensure_utc

current_user = Annotated[UserResponse, Depends(AuthService.get_current_user)]

user_service = Annotated[UserService, Depends(UserService)]
auth_service = Annotated[AuthService, Depends(AuthService)]
collector_service = Annotated[CollectorService, Depends(CollectorService)]
organization_service = Annotated[OrganizationService, Depends(OrganizationService)]
opc_server_service = Annotated[OpcServerService, Depends(OpcServerService)]
sensor_service = Annotated[SensorService, Depends(SensorService)]
reading_service = Annotated[ReadingService, Depends(ReadingService)]
alert_service = Annotated[AlertService, Depends(AlertService)]
alert_rule_service = Annotated[AlertRuleService, Depends(AlertRuleService)]
audit_log_service = Annotated[AuditLogService, Depends(AuditLogService)]
tenant_service = Annotated[TenantService, Depends(TenantService)]
ws_auth_service = Annotated[WsAuthService, Depends(WsAuthService)]


def limit_query_factory(max_limit: int = PAGINATION_MAX_PER_PAGE):
    """Factory for creating limit query parameters with a specified max limit."""
    return Query(PAGINATION_PER_PAGE, ge=1, le=max_limit, description=f"Number of items to return (max {max_limit})")


offset_query = Query(PAGINATION_DEFAULT_OFFSET, ge=0, description="Number of items to skip")
limit_query_default = limit_query_factory()
bucket_interval_query = Query(
    READINGS_DEFAULT_BUCKET_INTERVAL,
    pattern="^\\d+\\s+(second|seconds|minute|minutes|hour|hours)$",
    description=(
        f"Aggregation interval for time buckets. Allowed values: {', '.join(READINGS_ALLOWED_BUCKET_INTERVALS)}"
    ),
)
prefetch_window_minutes_query = Query(
    SENSOR_PREFETCH_DEFAULT_WINDOW_MINUTES,
    ge=1,
    le=SENSOR_PREFETCH_MAX_WINDOW_MINUTES,
    description=f"Prefetch readings for the last N minutes (max {SENSOR_PREFETCH_MAX_WINDOW_MINUTES})",
)


def get_readings_range(
    start_time: datetime | None = Query(None, description="Range start time. Defaults to end_time - 24h"),
    end_time: datetime | None = Query(None, description="Range end time. Defaults to current UTC time"),
) -> tuple[datetime, datetime]:
    datetime_now = datetime.now(timezone.utc)
    resolved_end = ensure_utc(end_time) if end_time else datetime_now
    resolved_start = (
        ensure_utc(start_time) if start_time else (resolved_end - timedelta(hours=READINGS_DEFAULT_RANGE_HOURS))
    )

    if resolved_start > resolved_end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_time must be less than or equal to end_time",
        )

    if (resolved_end - resolved_start) > timedelta(hours=READINGS_MAX_HOURS_WINDOW):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Time range cannot exceed {READINGS_MAX_HOURS_WINDOW} hours",
        )

    return resolved_start, resolved_end


def get_bucket_interval(
    bucket_interval: str = bucket_interval_query,
) -> str:
    if bucket_interval not in READINGS_ALLOWED_BUCKET_INTERVALS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"bucket_interval must be one of: {', '.join(READINGS_ALLOWED_BUCKET_INTERVALS)}",
        )
    return bucket_interval


async def get_tenant_id(
    user: current_user,
    service: tenant_service,
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
) -> UUID:
    """Extract and validate tenant ID from X-Tenant-ID header."""
    return await service.validate_and_get_tenant_id(x_tenant_id=x_tenant_id, user=user)


def get_uow() -> SQLUnitOfWork:
    """Get a general Unit of Work without tenant scoping."""
    return SQLUnitOfWork()


def get_tenant_uow(tenant_id: UUID = Depends(get_tenant_id)) -> SQLUnitOfWork:
    """Get a tenant-scoped Unit of Work."""
    return SQLUnitOfWork(tenant_id=tenant_id)


def get_admin_uow() -> SQLUnitOfWork:
    """Get a UnitOfWork that bypasses RLS for admin operations."""
    return SQLUnitOfWork(bypass_rls=True)


def get_connection_manager(websocket: WebSocket) -> ConnectionManager:
    """Retrieve the process-wide WebSocket ConnectionManager from app state."""
    return websocket.app.state.ws_manager


async def ws_authenticate(
    websocket: WebSocket,
    service: ws_auth_service,
    ticket: str = Query(..., description="Single-use WebSocket auth ticket"),
) -> tuple[UserResponse, UUID]:
    """Consume a Redis ticket and return the authenticated user and org."""
    return await service.authenticate_ticket(websocket, ticket)


TenantIdDep = Annotated[UUID, Depends(get_tenant_id)]
SQLUnitOfWorkDep = Annotated[SQLUnitOfWork, Depends(get_uow)]
TenantUnitOfWorkDep = Annotated[SQLUnitOfWork, Depends(get_tenant_uow)]
AdminUnitOfWorkDep = Annotated[SQLUnitOfWork, Depends(get_admin_uow)]
ConnectionManagerDep = Annotated[ConnectionManager, Depends(get_connection_manager)]
ws_authenticate_dep = Annotated[tuple[UserResponse, UUID], Depends(ws_authenticate)]
ReadingsRangeDep = Annotated[tuple[datetime, datetime], Depends(get_readings_range)]
BucketIntervalDep = Annotated[str, Depends(get_bucket_interval)]
