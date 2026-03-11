import asyncio

import orjson
from aio_pika.abc import AbstractIncomingMessage
from loguru import logger

from app.schemas.ws import WsBroadcastEvent
from app.uow.rabbitmq import RabbitMQUnitOfWork
from app.api.ws.manager import ConnectionManager

__all__ = ["start_ws_consumer"]


async def start_ws_consumer(manager: ConnectionManager) -> None:
    """Long-running background task that bridges RabbitMQ → WebSocket clients.

    Opens a single :class:`~app.uow.rabbitmq.RabbitMQUnitOfWork` for the
    entire FastAPI process lifetime.  The exclusive auto-delete queue is
    destroyed automatically on shutdown — no manual cleanup required.

    Every replica gets its own queue bound to the fanout exchange, so all
    replicas receive every broadcast without sticky sessions.
    """
    logger.info("WS consumer: starting")

    async def _handle(message: AbstractIncomingMessage) -> None:
        try:
            event = WsBroadcastEvent.model_validate(orjson.loads(message.body))
            await manager.broadcast_to_org(event.organization_id, event)
        except Exception:
            logger.exception("WS consumer: failed to process message")

    try:
        async with RabbitMQUnitOfWork() as rmq:
            logger.info("WS consumer: connected, waiting for events …")
            await rmq.consume.subscribe(_handle)
    except asyncio.CancelledError:
        logger.info("WS consumer: cancelled, shutting down")
        raise
    except Exception:
        logger.exception("WS consumer: unexpected error")
        raise
