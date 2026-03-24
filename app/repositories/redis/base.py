import asyncio

from redis.asyncio import Redis


class AbstractRedisRepository:
    def __init__(self, redis: Redis):
        self._redis = redis

    @property
    def redis(self) -> Redis:
        return self._redis


class BaseRedisRepository(AbstractRedisRepository):
    DEFAULT_TTL_SECONDS: int | None = None

    @staticmethod
    def _decode_value(value: bytes | str | None) -> str | None:
        if value is None:
            return None
        return value.decode() if isinstance(value, bytes) else str(value)

    @classmethod
    def _get_ttl(cls, ttl_seconds: int | None) -> int | None:
        return ttl_seconds if ttl_seconds is not None else cls.DEFAULT_TTL_SECONDS

    @staticmethod
    def _decode_bytes(data: dict) -> dict:
        return {
            (k.decode() if isinstance(k, bytes) else str(k)): (v.decode() if isinstance(v, bytes) else str(v))
            for k, v in data.items()
        }

    async def set(self, key: str, value: dict, ttl_seconds: int | None = None) -> None:
        await self._redis.hset(key, mapping=value)
        ttl = self._get_ttl(ttl_seconds)
        if ttl is not None:
            await self._redis.expire(key, ttl)

    async def mset(self, values_by_key: dict[str, dict], ttl_seconds: int | None = None) -> None:
        if not values_by_key:
            return

        await asyncio.gather(*(self._redis.hset(key, mapping=value) for key, value in values_by_key.items()))

        ttl = self._get_ttl(ttl_seconds)
        if ttl is not None:
            await asyncio.gather(*(self._redis.expire(key, ttl) for key in values_by_key))

    async def get(self, key: str) -> dict | None:
        item = await self._redis.hgetall(key)
        return self._decode_bytes(item) if item else None

    async def mget(self, keys: list[str], fields: list[str]) -> dict[str, dict[str, str]]:
        if not keys:
            return {}
        if not fields:
            return {key: {} for key in keys}

        values = await asyncio.gather(*(self._redis.hmget(key, fields) for key in keys))

        result: dict[str, dict[str, str]] = {}
        for key, row in zip(keys, values):
            decoded_row = {
                field: decoded
                for field, value in zip(fields, row)
                if (decoded := self._decode_value(value)) is not None
            }
            if decoded_row:
                result[key] = decoded_row
        return result

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def exists(self, key: str) -> bool:
        return await self._redis.exists(key) > 0

    async def set_raw(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        await self._redis.set(key, value, ex=self._get_ttl(ttl_seconds))

    async def mset_raw(self, values_by_key: dict[str, str], ttl_seconds: int | None = None) -> None:
        if not values_by_key:
            return

        ttl = self._get_ttl(ttl_seconds)
        if ttl is None:
            await self._redis.mset(values_by_key)
            return

        await asyncio.gather(*(self._redis.set(key, value, ex=ttl) for key, value in values_by_key.items()))

    async def get_raw(self, key: str) -> str | None:
        value = await self._redis.get(key)
        return self._decode_value(value)

    async def mget_raw(self, keys: list[str]) -> dict[str, str | None]:
        if not keys:
            return {}

        values = await self._redis.mget(keys)
        return {key: self._decode_value(value) for key, value in zip(keys, values)}

    async def delete_by_pattern(self, pattern: str) -> None:
        async for key in self._redis.scan_iter(match=pattern):
            key_str = key.decode() if isinstance(key, bytes) else key
            await self.delete(key_str)
