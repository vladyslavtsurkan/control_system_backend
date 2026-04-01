from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.dependencies import (
    TenantUnitOfWorkDep,
    TenantIdDep,
    current_user,
    offset_query,
    limit_query_default,
    prefetch_window_minutes_query,
    sensor_service,
)
from app.schemas.base import PaginatedResponse
from app.schemas.sensor import (
    SensorCreateRequest,
    SensorUpdateRequest,
    SensorControlRequest,
    SensorResponse,
    SensorWithReadingsResponse,
)

__all__ = ["router"]

router = APIRouter(prefix="/sensors", tags=["Sensors"])


@router.post("/", response_model=SensorResponse, status_code=status.HTTP_201_CREATED)
async def create_sensor(
    uow: TenantUnitOfWorkDep,
    tenant_id: TenantIdDep,
    user: current_user,
    request: SensorCreateRequest,
    service: sensor_service,
):
    """
    Create a new sensor for an OPC server.

    Requires X-Tenant-ID header. Only admin/owner.
    """
    return await service.create_sensor(uow=uow, tenant_id=tenant_id, current_user=user, request=request)


@router.get("/", response_model=PaginatedResponse[SensorWithReadingsResponse], status_code=status.HTTP_200_OK)
async def get_sensors(
    uow: TenantUnitOfWorkDep,
    tenant_id: TenantIdDep,
    service: sensor_service,
    opc_server_id: UUID | None = Query(None, description="Filter by OPC server ID"),
    is_writable: bool | None = Query(default=None, description="Filter sensors by their writable status"),
    offset: int = offset_query,
    limit: int = limit_query_default,
    prefetch_readings: bool = Query(False, description="Include recent readings for each sensor"),
    prefetch_window_minutes: int = prefetch_window_minutes_query,
):
    """
    Get all sensors for the current tenant.

    Requires X-Tenant-ID header.
    Optionally filter by OPC server ID.
    """
    return await service.get_sensors(
        uow=uow,
        tenant_id=tenant_id,
        opc_server_id=opc_server_id,
        is_writable=is_writable,
        offset=offset,
        limit=limit,
        prefetch_readings=prefetch_readings,
        prefetch_window_minutes=prefetch_window_minutes,
    )


@router.get("/{sensor_id}", response_model=SensorResponse, status_code=status.HTTP_200_OK)
async def get_sensor(
    uow: TenantUnitOfWorkDep,
    tenant_id: TenantIdDep,
    sensor_id: UUID,
    service: sensor_service,
):
    """
    Get a specific sensor by ID.

    Requires X-Tenant-ID header.
    """
    return await service.get_sensor(uow=uow, tenant_id=tenant_id, sensor_id=sensor_id)


@router.patch("/{sensor_id}", response_model=SensorResponse, status_code=status.HTTP_200_OK)
async def update_sensor(
    uow: TenantUnitOfWorkDep,
    tenant_id: TenantIdDep,
    sensor_id: UUID,
    user: current_user,
    request: SensorUpdateRequest,
    service: sensor_service,
):
    """
    Update a sensor.

    Requires X-Tenant-ID header. Only admin/owner.
    """
    return await service.update_sensor(
        uow=uow,
        tenant_id=tenant_id,
        sensor_id=sensor_id,
        current_user=user,
        request=request,
    )


@router.post("/{sensor_id}/control", status_code=status.HTTP_202_ACCEPTED)
async def control_sensor(
    uow: TenantUnitOfWorkDep,
    tenant_id: TenantIdDep,
    sensor_id: UUID,
    payload: SensorControlRequest,
    user: current_user,
    service: sensor_service,
):
    """Dispatch a control command to the edge for a specific sensor."""
    return await service.send_control_command(
        uow=uow,
        tenant_id=tenant_id,
        sensor_id=sensor_id,
        command_req=payload,
        current_user=user,
    )


@router.delete("/{sensor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sensor(
    uow: TenantUnitOfWorkDep,
    tenant_id: TenantIdDep,
    sensor_id: UUID,
    user: current_user,
    service: sensor_service,
):
    """
    Delete a sensor (soft delete).

    Requires X-Tenant-ID header. Only admin/owner.
    """
    await service.delete_sensor(uow=uow, tenant_id=tenant_id, sensor_id=sensor_id, current_user=user)
