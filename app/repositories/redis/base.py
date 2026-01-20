from redis.asyncio import Redis


class AbstractRedisRepository:
    def __init__(self, redis: Redis):
        self._redis = redis

    @property
    def redis(self) -> Redis:
        return self._redis


class BaseRedisRepository(AbstractRedisRepository):
    DEFAULT_TTL_SECONDS: int | None = None

    async def set(self, key: str, value: dict, ttl_seconds: int | None = None) -> None:
        await self._redis.hset(key, mapping=value)
        if ttl_seconds is not None or self.DEFAULT_TTL_SECONDS is not None:
            await self._redis.expire(key, ttl_seconds or self.DEFAULT_TTL_SECONDS)

    @staticmethod
    def _decode_bytes(data: dict) -> dict:
        return {k.decode(): v.decode() for k, v in data.items()}

    async def get(self, key: str) -> dict | None:
        item = await self._redis.hgetall(key)
        return self._decode_bytes(item) if item else None

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def exists(self, key: str) -> bool:
        return await self._redis.exists(key) > 0
