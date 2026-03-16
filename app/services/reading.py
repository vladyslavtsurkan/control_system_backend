import datetime
from uuid import UUID

from app.core.constants import (
    PAGINATION_PER_PAGE,
    READINGS_DEFAULT_BUCKET_INTERVAL,
    READINGS_BUCKET_INTERVAL_TO_TIMEDELTA,
)
from app.core.exc import ObjectNotFoundException
from app.schemas.base import PaginatedResponse
from app.schemas.reading import ReadingsBucketedResponse, AlertResponse
from app.services.mixins import TenantValidationMixin
from app.uow.sql import SQLUnitOfWork

__all__ = ["ReadingService", "AlertService"]


class ReadingService(TenantValidationMixin):
    @staticmethod
    def _to_utc_iso_z(ts: datetime.datetime) -> str:
        return ts.astimezone(datetime.UTC).isoformat().replace("+00:00", "Z")

    async def get_readings(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        sensor_id: UUID,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        bucket_interval: str = READINGS_DEFAULT_BUCKET_INTERVAL,
    ) -> ReadingsBucketedResponse:
        """Get readings for a sensor."""
        async with uow:
            await self._validate_sensor_tenant(uow, sensor_id, tenant_id)

            bucket_interval_td = READINGS_BUCKET_INTERVAL_TO_TIMEDELTA[bucket_interval]

            bucketed_readings = await uow.reading.get_in_time_range(
                sensor_id=sensor_id,
                start_time=start_time,
                end_time=end_time,
                bucket_interval=bucket_interval_td,
            )

            times = [self._to_utc_iso_z(row.time_bucket) for row in bucketed_readings]
            values = [float(row.avg_value) for row in bucketed_readings]
            return ReadingsBucketedResponse(times=times, values=values)


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
            await self._validate_active_organization(uow, tenant_id)

            alerts, count = await uow.alert.get_multi_for_tenant_with_rule(
                tenant_id=tenant_id,
                offset=offset,
                limit=limit,
                sensor_id=sensor_id,
                order_by="-id",
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
            alert = await uow.alert.get_for_tenant_with_rule(alert_id=alert_id, tenant_id=tenant_id)
            if not alert:
                raise ObjectNotFoundException(str(alert_id), "Alert")

            if alert.is_acknowledged:
                return AlertResponse.model_validate(alert)

            await uow.alert.update(
                filters={"id": alert_id},
                updates={"is_acknowledged": True},
            )
            updated = await uow.alert.get_for_tenant_with_rule(alert_id=alert_id, tenant_id=tenant_id)
            if not updated:
                raise ObjectNotFoundException(str(alert_id), "Alert")
            return AlertResponse.model_validate(updated)

    async def resolve_alert(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        alert_id: UUID,
    ) -> AlertResponse:
        """Mark an alert as resolved. Idempotent."""
        async with uow:
            alert = await uow.alert.get_for_tenant_with_rule(alert_id=alert_id, tenant_id=tenant_id)
            if not alert:
                raise ObjectNotFoundException(str(alert_id), "Alert")

            if alert.resolved_at is not None:
                return AlertResponse.model_validate(alert)

            await uow.alert.update(
                filters={"id": alert_id},
                updates={"resolved_at": datetime.datetime.now(datetime.UTC)},
            )
            updated = await uow.alert.get_for_tenant_with_rule(alert_id=alert_id, tenant_id=tenant_id)
            if not updated:
                raise ObjectNotFoundException(str(alert_id), "Alert")
            return AlertResponse.model_validate(updated)
