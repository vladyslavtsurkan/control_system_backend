import aio_pika
from aio_pika.abc import AbstractRobustConnection
from loguru import logger

from app.core.config import settings

__all__ = ["RabbitMQClient", "rabbitmq_client"]


class RabbitMQClient:
    """
    Persistent, lazily-initialized RabbitMQ connection.

    A single :class:`aio_pika.RobustConnection` is created on the first call
    to :meth:`get_connection` and reused thereafter.  ``aio_pika`` reconnects
    automatically on broker restarts, so callers never need to manage the
    connection lifecycle explicitly.
    """

    def __init__(self) -> None:
        self._config = settings.rabbitmq
        self._connection: AbstractRobustConnection | None = None

    async def get_connection(self) -> AbstractRobustConnection:
        if self._connection is None or self._connection.is_closed:
            logger.debug("RabbitMQClient: opening new robust connection")
            self._connection = await aio_pika.connect_robust(self._config.url)
        return self._connection

    async def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            logger.debug("RabbitMQClient: connection closed")


rabbitmq_client = RabbitMQClient()
