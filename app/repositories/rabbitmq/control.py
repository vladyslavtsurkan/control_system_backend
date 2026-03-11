import aio_pika

from app.core.config import settings
from app.repositories.rabbitmq.base import AbstractRabbitMQRepository

__all__ = ["ControlRepository"]


class ControlRepository(AbstractRabbitMQRepository):
    """Publishes control-plane messages to the ``iiot_control`` fanout exchange.

    Currently used to signal every FastStream worker process to hot-reload its
    in-memory alert-rule cache after any create / update / delete mutation.
    """

    async def publish_rule_invalidation(self) -> None:
        exchange = await self._channel.declare_exchange(
            settings.rabbitmq.CONTROL_EXCHANGE,
            aio_pika.ExchangeType.FANOUT,
            durable=True,
        )
        await exchange.publish(
            aio_pika.Message(body=b"rule_changed"),
            routing_key="",
        )
