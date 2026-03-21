import os
import socket

from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from app.core.config import settings

__all__ = [
    "broker",
    "control_exchange",
    "control_queue",
    "telemetry_exchange",
    "telemetry_queue",
]


broker = RabbitBroker(settings.rabbitmq.url)


def _build_control_queue() -> RabbitQueue:
    if settings.rabbitmq.CONTROL_QUEUE_MODE == "shared":
        return RabbitQueue(
            settings.rabbitmq.CONTROL_QUEUE,
            durable=True,
        )

    worker_queue_name = f"{settings.rabbitmq.CONTROL_QUEUE_PREFIX}.{socket.gethostname()}.{os.getpid()}"
    return RabbitQueue(
        worker_queue_name,
        durable=False,
        auto_delete=True,
    )


telemetry_exchange = RabbitExchange(
    settings.rabbitmq.TELEMETRY_EXCHANGE,
    type=ExchangeType.TOPIC,
    durable=True,
)
telemetry_queue = RabbitQueue(
    settings.rabbitmq.TELEMETRY_QUEUE,
    durable=True,
    routing_key=settings.rabbitmq.TELEMETRY_ROUTING_KEY,
)

control_exchange = RabbitExchange(
    settings.rabbitmq.CONTROL_EXCHANGE,
    type=ExchangeType.FANOUT,
    durable=True,
)
control_queue = _build_control_queue()
