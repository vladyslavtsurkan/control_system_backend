from uuid import UUID

from faststream.rabbit import RabbitMessage
from loguru import logger

from app.worker.common import convert_protobuf_to_telemetry
from app.worker.schemas.telemetry import TelemetryReading
from app.worker.services.rule_cache import rule_cache_service
from app.worker.services.sensor_cache import SensorCacheService
from app.worker.services.telemetry import process_telemetry_batch

__all__ = ["TelemetrySubscriberService"]


class TelemetrySubscriberService:
    """Orchestrates telemetry message handling for broker subscribers."""

    @staticmethod
    async def handle_control_message(msg: str) -> None:
        logger.info("Control message received: {msg}", msg=msg)
        await rule_cache_service.reload()

    async def handle_telemetry_message(self, message: RabbitMessage) -> None:
        org_uuid = self._extract_org_uuid_from_routing_key(message.raw_message.routing_key)
        if org_uuid is None:
            return

        readings_by_sensor_id = convert_protobuf_to_telemetry(message.raw_message.body)
        if not readings_by_sensor_id:
            logger.error("Failed to convert Protobuf batch, skipping processing")
            return

        sensor_org_map = await SensorCacheService.get_organizations_by_sensor_ids(set(readings_by_sensor_id))
        readings_to_process = self._filter_readings_for_org(
            readings_by_sensor_id=readings_by_sensor_id,
            sensor_org_map=sensor_org_map,
            organization_uuid=org_uuid,
        )
        if not readings_to_process:
            logger.debug(
                "Telemetry batch skipped: no readings mapped to organization {org_uuid}",
                org_uuid=org_uuid,
            )
            return

        reading_count, alert_count = await process_telemetry_batch(readings_to_process)
        logger.debug(
            "Batch processed for organization {org_uuid}: {readings} readings, {alerts} alerts",
            org_uuid=org_uuid,
            readings=reading_count,
            alerts=alert_count,
        )

    @staticmethod
    def _extract_org_uuid_from_routing_key(routing_key: str) -> UUID | None:
        routing_key_parts = routing_key.split(".")
        if len(routing_key_parts) < 2:
            logger.error("Invalid routing key format: {routing_key}", routing_key=routing_key)
            return None

        try:
            return UUID(routing_key_parts[1])
        except ValueError:
            logger.error("Spoofed or invalid UUID in routing key: {org_uuid}", org_uuid=routing_key_parts[1])
            return None

    @staticmethod
    def _filter_readings_for_org(
        readings_by_sensor_id: dict[UUID, list[TelemetryReading]],
        sensor_org_map: dict[UUID, UUID],
        organization_uuid: UUID,
    ) -> list[TelemetryReading]:
        readings_to_process: list[TelemetryReading] = []
        for sensor_id, readings in readings_by_sensor_id.items():
            if sensor_org_map.get(sensor_id) == organization_uuid:
                readings_to_process.extend(readings)
        return readings_to_process
