import datetime
from uuid import UUID

from app.core.constants import (
    PAGINATION_PER_PAGE,
    READINGS_DEFAULT_BUCKET_INTERVAL,
    READINGS_BUCKET_INTERVAL_TO_TIMEDELTA,
    SENSOR_PREFETCH_DEFAULT_WINDOW_MINUTES,
)
from app.core.exc import ObjectNotFoundException
from app.schemas.base import PaginatedResponse
from app.schemas.sensor import (
    SensorCreateRequest,
    SensorUpdateRequest,
    SensorResponse,
    SensorWithReadingsResponse,
)
from app.schemas.reading import ReadingsBucket, ReadingsBucketedResponse
from app.schemas.user import UserResponse
from app.services.mixins import TenantValidationMixin
from app.uow.sql import SQLUnitOfWork

__all__ = ["SensorService"]


class SensorService(TenantValidationMixin):
    @staticmethod
    def _to_utc_iso_z(ts: datetime.datetime) -> str:
        return ts.astimezone(datetime.UTC).isoformat().replace("+00:00", "Z")

    async def create_sensor(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        current_user: UserResponse,
        request: SensorCreateRequest,
    ) -> SensorResponse:
        """Create a new sensor for an OPC server. Only admin/owner."""
        async with uow:
            await self._check_admin_or_owner(uow, current_user.id, tenant_id)

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
        prefetch_readings: bool = False,
        prefetch_window_minutes: int = SENSOR_PREFETCH_DEFAULT_WINDOW_MINUTES,
    ) -> PaginatedResponse[SensorWithReadingsResponse]:
        """Get all sensors for the tenant, optionally filtered by OPC server."""
        async with uow:
            await SensorService._validate_active_organization(uow, tenant_id)

            sensors, count = await uow.sensor.get_multi_for_tenant(
                tenant_id=tenant_id,
                offset=offset,
                limit=limit,
                opc_server_id=opc_server_id,
            )

            sensor_readings: dict[UUID, ReadingsBucketedResponse] = {}
            if prefetch_readings and sensors:
                end_time = datetime.datetime.now(datetime.UTC)
                start_time = end_time - datetime.timedelta(minutes=prefetch_window_minutes)
                readings = await uow.reading.get_bucketed_for_sensors(
                    sensor_ids=[sensor.id for sensor in sensors],
                    start_time=start_time,
                    end_time=end_time,
                    bucket_interval=READINGS_BUCKET_INTERVAL_TO_TIMEDELTA[READINGS_DEFAULT_BUCKET_INTERVAL],
                )

                grouped: dict[UUID, ReadingsBucket] = {}
                for reading in readings:
                    if reading.avg_value is None:
                        continue
                    if reading.sensor_id not in grouped:
                        grouped[reading.sensor_id] = {"times": [], "values": []}
                    bucket = grouped[reading.sensor_id]
                    bucket["times"].append(SensorService._to_utc_iso_z(reading.time_bucket))
                    bucket["values"].append(float(reading.avg_value))

                sensor_readings = {
                    sensor_id: ReadingsBucketedResponse(times=data["times"], values=data["values"])
                    for sensor_id, data in grouped.items()
                }

            items: list[SensorWithReadingsResponse] = []
            for sensor in sensors:
                base_payload = SensorResponse.model_validate(sensor)
                payload = SensorWithReadingsResponse(**base_payload.model_dump())
                if prefetch_readings:
                    payload = payload.model_copy(
                        update={
                            "readings": sensor_readings.get(
                                sensor.id,
                                ReadingsBucketedResponse(times=[], values=[]),
                            )
                        }
                    )
                items.append(payload)

            return PaginatedResponse(
                items=items,
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
            sensor = await self._get_active_sensor_for_tenant(uow, sensor_id, tenant_id)
            if not sensor:
                raise ObjectNotFoundException(str(sensor_id), "Sensor")
            return SensorResponse.model_validate(sensor)

    async def update_sensor(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        sensor_id: UUID,
        current_user: UserResponse,
        request: SensorUpdateRequest,
    ) -> SensorResponse:
        """Update a sensor. Only admin/owner."""
        async with uow:
            await self._check_admin_or_owner(uow, current_user.id, tenant_id)
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
        current_user: UserResponse,
    ) -> None:
        """Soft delete a sensor. Only admin/owner."""
        async with uow:
            await self._check_admin_or_owner(uow, current_user.id, tenant_id)
            await self._validate_sensor_tenant(uow, sensor_id, tenant_id)

            sensor = await uow.sensor.update(
                filters={"id": sensor_id, "is_deleted": False},
                updates={"is_deleted": True},
            )
            if not sensor:
                raise ObjectNotFoundException(str(sensor_id), "Sensor")
