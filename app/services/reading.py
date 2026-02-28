from uuid import UUID

from app.core.constants import PAGINATION_PER_PAGE
from app.core.exc import ObjectNotFoundException
from app.schemas.base import PaginatedResponse
from app.schemas.reading import ReadingResponse, AlertResponse
from app.uow.sql import SQLUnitOfWork

__all__ = ["ReadingService", "AlertService"]


async def _validate_sensor_tenant(uow: SQLUnitOfWork, sensor_id: UUID, tenant_id: UUID) -> None:
    """Validate that a sensor belongs to the given tenant via its OPC server."""
    sensor = await uow.sensor.get(filters={"id": sensor_id})
    if not sensor:
        raise ObjectNotFoundException(str(sensor_id), "Sensor")
    opc_server = await uow.opc_server.get(filters={"id": sensor.opc_server_id, "organization_id": tenant_id})
    if not opc_server:
        raise ObjectNotFoundException(str(sensor_id), "Sensor")


class ReadingService:
    @staticmethod
    async def get_readings(
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        sensor_id: UUID,
        offset: int = 0,
        limit: int = PAGINATION_PER_PAGE,
    ) -> PaginatedResponse[ReadingResponse]:
        """Get readings for a sensor."""
        async with uow:
            await _validate_sensor_tenant(uow, sensor_id, tenant_id)

            readings, count = await uow.reading.get_multi(
                offset=offset,
                limit=limit,
                sensor_id=sensor_id,
                order_by="-time",
            )
            return PaginatedResponse(
                items=[ReadingResponse.model_validate(r) for r in readings],
                count=count,
                per_page=limit,
            )


class AlertService:
    @staticmethod
    async def get_alerts(
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        sensor_id: UUID | None = None,
        offset: int = 0,
        limit: int = PAGINATION_PER_PAGE,
    ) -> PaginatedResponse[AlertResponse]:
        """Get alerts for the tenant, optionally filtered by sensor."""
        async with uow:
            if sensor_id:
                await _validate_sensor_tenant(uow, sensor_id, tenant_id)
                filters = {"sensor_id": sensor_id}
            else:
                # Get all sensors belonging to the tenant's OPC servers
                tenant_servers, _ = await uow.opc_server.get_multi(
                    is_deleted=False, organization_id=tenant_id, limit=10000
                )
                server_ids = [s.id for s in tenant_servers]
                if not server_ids:
                    return PaginatedResponse(items=[], count=0, per_page=limit)
                tenant_sensors, _ = await uow.sensor.get_multi(opc_server_id__in=server_ids, limit=10000)
                sensor_ids = [s.id for s in tenant_sensors]
                if not sensor_ids:
                    return PaginatedResponse(items=[], count=0, per_page=limit)
                filters = {"sensor_id__in": sensor_ids}

            alerts, count = await uow.alert.get_multi(
                offset=offset,
                limit=limit,
                order_by="-created_at",
                **filters,
            )
            return PaginatedResponse(
                items=[AlertResponse.model_validate(a) for a in alerts],
                count=count,
                per_page=limit,
            )
