from typing import Self

from app.infra.redis import redis_client
from app.repositories.redis.alert_state import AlertStateRepository
from app.repositories.redis.verification import VerificationRepository
from app.repositories.redis.ws_ticket import WsTicketRepository
from app.uow.base import ABCUnitOfWork


class RedisUnitOfWork(ABCUnitOfWork):
    def __init__(self) -> None:
        self._client = redis_client
        self.redis = None

    async def __aenter__(self) -> Self:
        self.redis = self._client.get_client()
        self.verification = VerificationRepository(redis=self.redis)
        self.ws_ticket = WsTicketRepository(redis=self.redis)
        self.alert_state = AlertStateRepository(redis=self.redis)
        return self

    async def __aexit__(self, exc_type: any, exc: any, tb: any) -> None:
        if exc:
            raise exc
