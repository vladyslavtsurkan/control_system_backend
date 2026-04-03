import datetime
import time
from uuid import UUID, uuid4

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
    SensorControlRequest,
    SensorResponse,
    SensorWithReadingsResponse,
)
from app.schemas.reading import ReadingsBucket, ReadingsBucketedResponse
from app.schemas.user import UserResponse
from app.services.mixins import TenantValidationMixin
from app.uow.rabbitmq import RabbitMQUnitOfWork
from app.uow.sql import SQLUnitOfWork
from app.worker.generated import telemetry_pb2

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
            data["organization_id"] = tenant_id
            sensor = await uow.sensor.create(data)
            return SensorResponse.model_validate(sensor)

    @staticmethod
    async def get_sensors(
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        opc_server_id: UUID | None = None,
        is_writable: bool | None = None,
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
                is_writable=is_writable,
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

    async def send_control_command(
        self,
        uow: SQLUnitOfWork,
        tenant_id: UUID,
        sensor_id: UUID,
        command_req: SensorControlRequest,
        current_user: UserResponse,
    ) -> dict[str, str]:
        """Send a tenant-scoped control command to the edge for a sensor."""
        async with uow:
            await self._validate_active_organization(uow, tenant_id)

            sensor = await uow.sensor.get(filters={"id": sensor_id, "is_deleted": False})
            if not sensor:
                raise ObjectNotFoundException(str(sensor_id), "Sensor")

            # Tenant identity comes from X-Tenant-ID; users can belong to multiple orgs.
            sensor_for_tenant = await self._get_active_sensor_for_tenant(uow, sensor_id=sensor_id, tenant_id=tenant_id)
            if not sensor_for_tenant:
                raise ObjectNotFoundException(str(sensor_id), "Sensor")

        command_id = uuid4()
        cmd = telemetry_pb2.ControlCommand(  # type: ignore[attr-defined]
            command_id=str(command_id),
            sensor_id=str(sensor_id),
            timestamp=int(time.time()),
        )

        value = command_req.value
        if isinstance(value, bool):
            cmd.bool_val = value
        elif isinstance(value, int):
            cmd.int_val = value
        elif isinstance(value, float):
            cmd.float_val = value
        else:
            cmd.str_val = value

        async with RabbitMQUnitOfWork() as rmq:
            await rmq.control.publish_command(organization_id=tenant_id, payload=cmd.SerializeToString())

        return {"status": "Command dispatched", "command_id": str(command_id)}
