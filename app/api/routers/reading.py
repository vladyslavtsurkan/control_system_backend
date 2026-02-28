from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.dependencies import (
    TenantUnitOfWorkDep,
    TenantIdDep,
    offset_query,
    limit_query,
    reading_service,
    alert_service,
)
from app.schemas.base import PaginatedResponse
from app.schemas.reading import ReadingResponse, AlertResponse

__all__ = ["readings_router", "alerts_router"]

readings_router = APIRouter(prefix="/readings", tags=["Readings"])
alerts_router = APIRouter(prefix="/alerts", tags=["Alerts"])


@readings_router.get("/", response_model=PaginatedResponse[ReadingResponse], status_code=status.HTTP_200_OK)
async def get_readings(
    uow: TenantUnitOfWorkDep,
    tenant_id: TenantIdDep,
    service: reading_service,
    sensor_id: UUID = Query(..., description="Sensor ID to get readings for"),
    offset: int = offset_query,
    limit: int = limit_query,
):
    """Get readings for a sensor.

    Requires X-Tenant-ID header.
    """
    return await service.get_readings(uow=uow, tenant_id=tenant_id, sensor_id=sensor_id, offset=offset, limit=limit)


@alerts_router.get("/", response_model=PaginatedResponse[AlertResponse], status_code=status.HTTP_200_OK)
async def get_alerts(
    uow: TenantUnitOfWorkDep,
    tenant_id: TenantIdDep,
    service: alert_service,
    sensor_id: UUID | None = Query(None, description="Filter by sensor ID"),
    offset: int = offset_query,
    limit: int = limit_query,
):
    """Get alerts for the current tenant.

    Requires X-Tenant-ID header.
    Optionally filter by sensor ID.
    """
    return await service.get_alerts(uow=uow, tenant_id=tenant_id, sensor_id=sensor_id, offset=offset, limit=limit)
