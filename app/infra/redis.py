from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from app.core.config import settings

__all__ = ["RedisClient", "redis_client"]


class RedisClient:
    def __init__(self) -> None:
        self._config = settings.redis
        self._pool = ConnectionPool(
            host=self._config.HOST,
            port=self._config.PORT,
            db=self._config.DB,
            password=self._config.PASSWORD,
            max_connections=self._config.MAX_CONNECTIONS,
        )

    def get_client(self) -> Redis:
        return Redis(connection_pool=self._pool)


redis_client = RedisClient()
