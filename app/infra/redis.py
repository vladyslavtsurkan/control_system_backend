from redis.asyncio import Redis
from redis.asyncio.connection import BlockingConnectionPool

from app.core.config import settings

__all__ = ["RedisClient", "redis_client"]


class RedisClient:
    def __init__(self) -> None:
        self._config = settings.redis
        self._pool = BlockingConnectionPool(
            host=self._config.HOST,
            port=self._config.PORT,
            db=self._config.DB,
            password=self._config.PASSWORD,
            max_connections=self._config.MAX_CONNECTIONS,
            timeout=self._config.BLOCKING_TIMEOUT_SECONDS,
        )
        # Reuse one async Redis client per process to avoid unnecessary wrappers.
        self._client = Redis(connection_pool=self._pool)

    def get_client(self) -> Redis:
        return self._client

    async def close(self) -> None:
        await self._client.aclose()


redis_client = RedisClient()
