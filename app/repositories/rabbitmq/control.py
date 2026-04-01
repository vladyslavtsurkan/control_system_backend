from uuid import UUID

import aio_pika
from aio_pika.abc import AbstractExchange

from app.core.config import settings
from app.repositories.rabbitmq.base import AbstractRabbitMQRepository

__all__ = ["ControlRepository"]


class ControlRepository(AbstractRabbitMQRepository):
    """Publishes control-plane messages for worker invalidation and edge commands."""

    def __init__(self, channel: aio_pika.abc.AbstractChannel) -> None:
        super().__init__(channel)
        self._invalidation_exchange: AbstractExchange | None = None
        self._command_exchange: AbstractExchange | None = None

    async def _get_invalidation_exchange(self) -> AbstractExchange:
        if self._invalidation_exchange is None:
            self._invalidation_exchange = await self._declare_exchange(settings.rabbitmq.CONTROL_EXCHANGE)
        return self._invalidation_exchange

    async def _get_command_exchange(self) -> AbstractExchange:
        if self._command_exchange is None:
            self._command_exchange = await self._declare_exchange(
                settings.rabbitmq.CONTROL_COMMAND_EXCHANGE,
                exchange_type=aio_pika.ExchangeType.TOPIC,
                durable=True,
            )
        return self._command_exchange

    async def publish_rule_invalidation(self) -> None:
        exchange = await self._get_invalidation_exchange()
        await self._publish(exchange, b"rule_changed", content_type="text/plain")

    async def publish_command(self, organization_id: UUID, payload: bytes) -> None:
        exchange = await self._get_command_exchange()
        await self._publish(
            exchange,
            payload,
            routing_key=f"control.{organization_id}",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/x-protobuf",
        )
