from abc import ABC

from aio_pika.abc import AbstractChannel

__all__ = ["AbstractRabbitMQRepository"]


class AbstractRabbitMQRepository(ABC):
    """Base for all RabbitMQ repositories.

    A single channel is injected once per :class:`~app.uow.rabbitmq.RabbitMQUnitOfWork`
    context and shared across all publish calls within that unit of work —
    this avoids per-call channel creation overhead under high throughput.
    """

    def __init__(self, channel: AbstractChannel) -> None:
        self._channel = channel
