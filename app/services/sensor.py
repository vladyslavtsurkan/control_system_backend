from uuid import UUID

from app.core.constants import PAGINATION_PER_PAGE
from app.core.exc import ObjectNotFoundException
from app.schemas.base import PaginatedResponse
from app.schemas.sensor import (
    SensorCreateRequest,
    SensorUpdateRequest,
    SensorResponse,
)
from app.services.base import TenantValidationMixin
from app.uow.sql import SQLUnitOfWork

__all__ = ["SensorService"]


class SensorService(TenantValidationMixin):
    @staticmethod
    async def create_sensor(
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        request: SensorCreateRequest,
    ) -> SensorResponse:
        """Create a new sensor for an OPC server."""
        async with uow:
            # Validate the OPC server belongs to the tenant
            opc_server = await uow.opc_server.get(
                filters={"id": request.opc_server_id, "is_deleted": False, "organization_id": tenant_id}
            )
            if not opc_server:
                raise ObjectNotFoundException(str(request.opc_server_id), "OpcServer")

            data = request.model_dump()
            sensor = await uow.sensor.create(data)
            return SensorResponse.model_validate(sensor)

    @staticmethod
    async def get_sensors(
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        opc_server_id: UUID | None = None,
        offset: int = 0,
        limit: int = PAGINATION_PER_PAGE,
    ) -> PaginatedResponse[SensorResponse]:
        """Get all sensors for the tenant, optionally filtered by OPC server."""
        async with uow:
            if opc_server_id:
                # Validate the OPC server belongs to the tenant
                opc_server = await uow.opc_server.get(
                    filters={"id": opc_server_id, "is_deleted": False, "organization_id": tenant_id}
                )
                if not opc_server:
                    raise ObjectNotFoundException(str(opc_server_id), "OpcServer")
                filters = {"is_deleted": False, "opc_server_id": opc_server_id}
            else:
                # Get all OPC server IDs for this tenant
                tenant_servers, _ = await uow.opc_server.get_multi(
                    is_deleted=False, organization_id=tenant_id, limit=10000
                )
                server_ids = [s.id for s in tenant_servers]
                if not server_ids:
                    return PaginatedResponse(items=[], count=0, per_page=limit)
                filters = {"is_deleted": False, "opc_server_id__in": server_ids}

            sensors, count = await uow.sensor.get_multi(
                offset=offset,
                limit=limit,
                **filters,
            )
            return PaginatedResponse(
                items=[SensorResponse.model_validate(s) for s in sensors],
                count=count,
                per_page=limit,
            )

    async def get_sensor(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        sensor_id: UUID,
    ) -> SensorResponse:
        """Get a specific sensor by ID."""
        async with uow:
            await self._validate_sensor_tenant(uow, sensor_id, tenant_id)
            sensor = await uow.sensor.get(filters={"id": sensor_id, "is_deleted": False})
            return SensorResponse.model_validate(sensor)

    async def update_sensor(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        sensor_id: UUID,
        request: SensorUpdateRequest,
    ) -> SensorResponse:
        """Update a sensor."""
        async with uow:
            await self._validate_sensor_tenant(uow, sensor_id, tenant_id)
            updates = request.model_dump(exclude_unset=True)
            sensor = await uow.sensor.update(
                filters={"id": sensor_id, "is_deleted": False},
                updates=updates,
            )
            if not sensor:
                raise ObjectNotFoundException(str(sensor_id), "Sensor")
            return SensorResponse.model_validate(sensor)

    async def delete_sensor(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        sensor_id: UUID,
    ) -> None:
        """Soft delete a sensor."""
        async with uow:
            await self._validate_sensor_tenant(uow, sensor_id, tenant_id)
            sensor = await uow.sensor.update(
                filters={"id": sensor_id, "is_deleted": False},
                updates={"is_deleted": True},
            )
            if not sensor:
                raise ObjectNotFoundException(str(sensor_id), "Sensor")
