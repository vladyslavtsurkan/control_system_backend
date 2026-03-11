import orjson
import aio_pika
from aio_pika.abc import AbstractExchange

from app.core.config import settings
from app.repositories.rabbitmq.base import AbstractRabbitMQRepository
from app.schemas.ws import WsBroadcastEvent

__all__ = ["BroadcastRepository"]


class BroadcastRepository(AbstractRabbitMQRepository):
    """Publishes :class:`~app.schemas.ws.WsBroadcastEvent` objects to the
    WS broadcast fanout exchange.

    The exchange is declared and cached on the first :meth:`publish` call so
    the UoW can instantiate the repository cheaply before knowing whether any
    events will actually be published.
    """

    def __init__(self, channel: aio_pika.abc.AbstractChannel) -> None:
        super().__init__(channel)
        self._exchange: AbstractExchange | None = None

    async def _get_exchange(self) -> AbstractExchange:
        if self._exchange is None:
            self._exchange = await self._channel.declare_exchange(
                settings.rabbitmq.WS_BROADCAST_EXCHANGE,
                aio_pika.ExchangeType.FANOUT,
                durable=True,
            )
        return self._exchange

    async def publish(self, event: WsBroadcastEvent) -> None:
        exchange = await self._get_exchange()
        body = orjson.dumps(event.model_dump(mode="json"))
        await exchange.publish(
            aio_pika.Message(
                body=body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            ),
            routing_key="",
        )
