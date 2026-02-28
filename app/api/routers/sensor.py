from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.dependencies import (
    TenantUnitOfWorkDep,
    TenantIdDep,
    offset_query,
    limit_query,
    sensor_service,
)
from app.schemas.base import PaginatedResponse
from app.schemas.sensor import (
    SensorCreateRequest,
    SensorUpdateRequest,
    SensorResponse,
)

__all__ = ["router"]

router = APIRouter(prefix="/sensors", tags=["Sensors"])


@router.post("/", response_model=SensorResponse, status_code=status.HTTP_201_CREATED)
async def create_sensor(
    uow: TenantUnitOfWorkDep,
    tenant_id: TenantIdDep,
    request: SensorCreateRequest,
    service: sensor_service,
):
    """Create a new sensor for an OPC server.

    Requires X-Tenant-ID header.
    """
    return await service.create_sensor(uow=uow, tenant_id=tenant_id, request=request)


@router.get("/", response_model=PaginatedResponse[SensorResponse], status_code=status.HTTP_200_OK)
async def get_sensors(
    uow: TenantUnitOfWorkDep,
    tenant_id: TenantIdDep,
    service: sensor_service,
    opc_server_id: UUID | None = Query(None, description="Filter by OPC server ID"),
    offset: int = offset_query,
    limit: int = limit_query,
):
    """Get all sensors for the current tenant.

    Requires X-Tenant-ID header.
    Optionally filter by OPC server ID.
    """
    return await service.get_sensors(
        uow=uow, tenant_id=tenant_id, opc_server_id=opc_server_id, offset=offset, limit=limit
    )


@router.get("/{sensor_id}", response_model=SensorResponse, status_code=status.HTTP_200_OK)
async def get_sensor(
    uow: TenantUnitOfWorkDep,
    tenant_id: TenantIdDep,
    sensor_id: UUID,
    service: sensor_service,
):
    """Get a specific sensor by ID.

    Requires X-Tenant-ID header.
    """
    return await service.get_sensor(uow=uow, tenant_id=tenant_id, sensor_id=sensor_id)


@router.patch("/{sensor_id}", response_model=SensorResponse, status_code=status.HTTP_200_OK)
async def update_sensor(
    uow: TenantUnitOfWorkDep,
    tenant_id: TenantIdDep,
    sensor_id: UUID,
    request: SensorUpdateRequest,
    service: sensor_service,
):
    """Update a sensor.

    Requires X-Tenant-ID header.
    """
    return await service.update_sensor(uow=uow, tenant_id=tenant_id, sensor_id=sensor_id, request=request)


@router.delete("/{sensor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sensor(
    uow: TenantUnitOfWorkDep,
    tenant_id: TenantIdDep,
    sensor_id: UUID,
    service: sensor_service,
):
    """Delete a sensor (soft delete).

    Requires X-Tenant-ID header.
    """
    await service.delete_sensor(uow=uow, tenant_id=tenant_id, sensor_id=sensor_id)
