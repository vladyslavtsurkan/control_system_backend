from abc import ABC

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractExchange, AbstractQueue

__all__ = ["AbstractRabbitMQRepository"]


class AbstractRabbitMQRepository(ABC):
    """Base for all RabbitMQ repositories.

    A single channel is injected once per :class:`~app.uow.rabbitmq.RabbitMQUnitOfWork`
    context and shared across all publish calls within that unit of work —
    this avoids per-call channel creation overhead under high throughput.

    Subclasses use the protected helpers :meth:`_declare_exchange`,
    :meth:`_declare_queue`, and :meth:`_publish` instead of accessing
    ``self._channel`` directly.
    """

    def __init__(self, channel: AbstractChannel) -> None:
        self._channel = channel

    async def _declare_exchange(
        self,
        name: str,
        exchange_type: aio_pika.ExchangeType = aio_pika.ExchangeType.FANOUT,
        durable: bool = True,
    ) -> AbstractExchange:
        """Declare and return an exchange on the current channel."""
        return await self._channel.declare_exchange(name, exchange_type, durable=durable)

    async def _declare_queue(
        self,
        name: str = "",
        durable: bool = False,
        exclusive: bool = False,
        auto_delete: bool = False,
    ) -> AbstractQueue:
        """Declare and return a queue on the current channel."""
        return await self._channel.declare_queue(
            name,
            durable=durable,
            exclusive=exclusive,
            auto_delete=auto_delete,
        )

    @staticmethod
    async def _publish(
        exchange: AbstractExchange,
        body: bytes,
        routing_key: str = "",
        delivery_mode: aio_pika.DeliveryMode = aio_pika.DeliveryMode.PERSISTENT,
        content_type: str = "application/json",
    ) -> None:
        """Publish a pre-serialized *body* to *exchange*."""
        await exchange.publish(
            aio_pika.Message(
                body=body,
                delivery_mode=delivery_mode,
                content_type=content_type,
            ),
            routing_key=routing_key,
        )
