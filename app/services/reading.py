import datetime
from uuid import UUID

from app.core.constants import PAGINATION_PER_PAGE
from app.core.exc import ObjectNotFoundException
from app.schemas.base import PaginatedResponse
from app.schemas.reading import ReadingResponse, AlertResponse
from app.services.base import TenantValidationMixin
from app.uow.sql import SQLUnitOfWork

__all__ = ["ReadingService", "AlertService"]


class ReadingService(TenantValidationMixin):
    async def get_readings(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        sensor_id: UUID,
        offset: int = 0,
        limit: int = PAGINATION_PER_PAGE,
    ) -> PaginatedResponse[ReadingResponse]:
        """Get readings for a sensor."""
        async with uow:
            await self._validate_sensor_tenant(uow, sensor_id, tenant_id)

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


class AlertService(TenantValidationMixin):
    async def get_alerts(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        sensor_id: UUID | None = None,
        offset: int = 0,
        limit: int = PAGINATION_PER_PAGE,
    ) -> PaginatedResponse[AlertResponse]:
        """Get alerts for the tenant, optionally filtered by sensor."""
        async with uow:
            if sensor_id:
                await self._validate_sensor_tenant(uow, sensor_id, tenant_id)
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
                order_by="-id",
                **filters,
            )
            return PaginatedResponse(
                items=[AlertResponse.model_validate(a) for a in alerts],
                count=count,
                per_page=limit,
            )

    async def acknowledge_alert(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        alert_id: UUID,
    ) -> AlertResponse:
        """Mark an alert as acknowledged. Idempotent."""
        async with uow:
            alert = await uow.alert.get(filters={"id": alert_id})
            if not alert:
                raise ObjectNotFoundException(str(alert_id), "Alert")
            await self._validate_sensor_tenant(uow, alert.sensor_id, tenant_id)

            if alert.is_acknowledged:
                return AlertResponse.model_validate(alert)

            updated = await uow.alert.update(
                filters={"id": alert_id},
                updates={"is_acknowledged": True},
            )
            return AlertResponse.model_validate(updated)

    async def resolve_alert(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        alert_id: UUID,
    ) -> AlertResponse:
        """Mark an alert as resolved. Idempotent."""
        async with uow:
            alert = await uow.alert.get(filters={"id": alert_id})
            if not alert:
                raise ObjectNotFoundException(str(alert_id), "Alert")
            await self._validate_sensor_tenant(uow, alert.sensor_id, tenant_id)

            if alert.resolved_at is not None:
                return AlertResponse.model_validate(alert)

            updated = await uow.alert.update(
                filters={"id": alert_id},
                updates={"resolved_at": datetime.datetime.now(datetime.UTC)},
            )
            return AlertResponse.model_validate(updated)
