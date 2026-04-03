import time

from faststream import Depends
from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue, RabbitMessage
from loguru import logger

from app.worker.services import TelemetrySubscriberService

__all__ = ["register_subscribers"]


def register_subscribers(
    broker: RabbitBroker,
    telemetry_queue: RabbitQueue,
    telemetry_exchange: RabbitExchange,
    control_queue: RabbitQueue,
    control_exchange: RabbitExchange,
) -> None:
    @broker.subscriber(telemetry_queue, telemetry_exchange)
    async def handle_telemetry(
        message: RabbitMessage,
        telemetry_service=Depends(TelemetrySubscriberService),
    ) -> None:
        time_start = time.perf_counter()
        await telemetry_service.handle_telemetry_message(message)
        time_end = time.perf_counter()
        logger.info(f"Handled telemetry message in {time_end - time_start:.3f} seconds")

    @broker.subscriber(control_queue, control_exchange)
    async def handle_control(msg: str, telemetry_service=Depends(TelemetrySubscriberService)) -> None:
        await telemetry_service.handle_control_message(msg)
