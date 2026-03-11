from typing import Self

from loguru import logger

from app.infra.rabbitmq import rabbitmq_client
from app.repositories.rabbitmq.broadcast import BroadcastRepository
from app.repositories.rabbitmq.consume import ConsumeRepository
from app.repositories.rabbitmq.control import ControlRepository
from app.uow.base import ABCUnitOfWork

__all__ = ["RabbitMQUnitOfWork"]


class RabbitMQUnitOfWork(ABCUnitOfWork):
    """Unit of Work for RabbitMQ publishing and consuming.

    A **single channel** is opened per context-manager invocation and shared
    across all repository calls within that unit of work.  This is the key
    high-throughput optimisation: a batch of N telemetry events pays the
    channel-open cost exactly once regardless of N.

    Usage::

        async with RabbitMQUnitOfWork() as rmq:
            await asyncio.gather(*[rmq.broadcast.publish(e) for e in events])
    """

    def __init__(self) -> None:
        self._channel = None

    async def __aenter__(self) -> Self:
        connection = await rabbitmq_client.get_connection()
        self._channel = await connection.channel()
        self.broadcast = BroadcastRepository(channel=self._channel)
        self.consume = ConsumeRepository(channel=self._channel)
        self.control = ControlRepository(channel=self._channel)
        return self

    async def __aexit__(self, exc_type: any, exc: any, tb: any) -> None:
        if self._channel and not self._channel.is_closed:
            try:
                await self._channel.close()
            except Exception:
                logger.exception("RabbitMQUnitOfWork: error closing channel")
        if exc:
            raise exc
