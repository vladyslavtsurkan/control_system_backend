from uuid import UUID

from app.core.exc import ObjectNotFoundException
from app.uow.sql import SQLUnitOfWork

__all__ = ["TenantValidationMixin"]


class TenantValidationMixin:
    """Mixin providing common tenant-scoped validation helpers."""

    @staticmethod
    async def _validate_sensor_tenant(uow: SQLUnitOfWork, sensor_id: UUID, tenant_id: UUID) -> None:
        """Validate that a sensor belongs to the given tenant via its OPC server."""
        sensor = await uow.sensor.get(filters={"id": sensor_id, "is_deleted": False})
        if not sensor:
            raise ObjectNotFoundException(str(sensor_id), "Sensor")
        opc_server = await uow.opc_server.get(filters={"id": sensor.opc_server_id, "organization_id": tenant_id})
        if not opc_server:
            raise ObjectNotFoundException(str(sensor_id), "Sensor")
