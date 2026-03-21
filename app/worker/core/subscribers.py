from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue
from loguru import logger

from app.worker.cache.rule_cache import rule_cache
from app.worker.services.telemetry import process_telemetry_batch
from app.worker.common import convert_protobuf_to_telemetry

__all__ = ["register_subscribers"]


def register_subscribers(
    broker: RabbitBroker,
    telemetry_queue: RabbitQueue,
    telemetry_exchange: RabbitExchange,
    control_queue: RabbitQueue,
    control_exchange: RabbitExchange,
) -> None:
    @broker.subscriber(telemetry_queue, telemetry_exchange)
    async def handle_telemetry(msg: bytes) -> None:
        batch = convert_protobuf_to_telemetry(msg)

        reading_count, alert_count = await process_telemetry_batch(batch)
        logger.debug(
            "Batch processed: {readings} readings, {alerts} alerts",
            readings=reading_count,
            alerts=alert_count,
        )

    @broker.subscriber(control_queue, control_exchange)
    async def handle_control(msg: str) -> None:
        logger.info("Control message received: {msg}", msg=msg)
        await rule_cache.reload()
