from uuid import UUID

from app.core.constants import PAGINATION_PER_PAGE
from app.core.exc import ObjectNotFoundException
from app.schemas.base import PaginatedResponse
from app.schemas.sensor import (
    SensorCreateRequest,
    SensorUpdateRequest,
    SensorResponse,
)
from app.uow.sql import SQLUnitOfWork

__all__ = ["SensorService"]


class SensorService:
    @staticmethod
    async def create_sensor(
        uow: SQLUnitOfWork,
        request: SensorCreateRequest,
    ) -> SensorResponse:
        """Create a new sensor for an OPC server."""
        async with uow:
            data = request.model_dump()
            sensor = await uow.sensor.create(data)
            return SensorResponse.model_validate(sensor)

    @staticmethod
    async def get_sensors(
        uow: SQLUnitOfWork,
        opc_server_id: UUID | None = None,
        offset: int = 0,
        limit: int = PAGINATION_PER_PAGE,
    ) -> PaginatedResponse[SensorResponse]:
        """Get all sensors (filtered by RLS and optionally by OPC server)."""
        async with uow:
            filters = {"is_deleted": False}
            if opc_server_id:
                filters["opc_server_id"] = opc_server_id

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

    @staticmethod
    async def get_sensor(
        uow: SQLUnitOfWork,
        sensor_id: UUID,
    ) -> SensorResponse:
        """Get a specific sensor by ID."""
        async with uow:
            sensor = await uow.sensor.get(filters={"id": sensor_id, "is_deleted": False})
            if not sensor:
                raise ObjectNotFoundException(str(sensor_id), "Sensor")
            return SensorResponse.model_validate(sensor)

    @staticmethod
    async def update_sensor(
        uow: SQLUnitOfWork,
        sensor_id: UUID,
        request: SensorUpdateRequest,
    ) -> SensorResponse:
        """Update a sensor."""
        async with uow:
            updates = request.model_dump(exclude_unset=True)
            sensor = await uow.sensor.update(
                filters={"id": sensor_id, "is_deleted": False},
                updates=updates,
            )
            if not sensor:
                raise ObjectNotFoundException(str(sensor_id), "Sensor")
            return SensorResponse.model_validate(sensor)

    @staticmethod
    async def delete_sensor(
        uow: SQLUnitOfWork,
        sensor_id: UUID,
    ) -> None:
        """Soft delete a sensor."""
        async with uow:
            sensor = await uow.sensor.update(
                filters={"id": sensor_id, "is_deleted": False},
                updates={"is_deleted": True},
            )
            if not sensor:
                raise ObjectNotFoundException(str(sensor_id), "Sensor")
