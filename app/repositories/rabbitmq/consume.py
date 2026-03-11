import asyncio
from collections.abc import Callable, Awaitable

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from app.core.config import settings
from app.repositories.rabbitmq.base import AbstractRabbitMQRepository

__all__ = ["ConsumeRepository"]

MessageHandler = Callable[[AbstractIncomingMessage], Awaitable[None]]


class ConsumeRepository(AbstractRabbitMQRepository):
    """Subscribes to the WS broadcast fanout exchange.

    Each FastAPI replica declares its own *exclusive*, *auto-delete* queue so
    that every replica receives all broadcast messages, enabling horizontal
    scaling without sticky sessions.  The queue is destroyed automatically
    when the channel (and therefore the connection) closes.
    """

    async def subscribe(self, handler: MessageHandler) -> None:
        """Declare an exclusive queue, bind it to the broadcast exchange, and
        consume messages indefinitely by calling *handler* for each one.

        This coroutine runs until cancelled (e.g. during FastAPI shutdown).
        Messages are acked *after* a successful handler invocation; on
        exception the message is nacked with ``requeue=False`` so it is
        discarded rather than looping forever.
        """
        exchange = await self._channel.declare_exchange(
            settings.rabbitmq.WS_BROADCAST_EXCHANGE,
            aio_pika.ExchangeType.FANOUT,
            durable=True,
        )

        # Exclusive + auto-delete: one queue per FastAPI process replica.
        queue = await self._channel.declare_queue(exclusive=True, auto_delete=True)
        await queue.bind(exchange)

        async with queue.iterator() as it:
            async for message in it:
                try:
                    await handler(message)
                    await message.ack()
                except asyncio.CancelledError:
                    await message.nack(requeue=False)
                    raise
                except Exception:
                    await message.nack(requeue=False)
