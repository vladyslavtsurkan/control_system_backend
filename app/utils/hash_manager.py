from argon2 import PasswordHasher, Type, DEFAULT_TIME_COST, DEFAULT_MEMORY_COST, DEFAULT_PARALLELISM
from argon2.exceptions import VerifyMismatchError, InvalidHash

from app.core.constants import (
    COLLECTOR_HASHER_TIME_COST,
    COLLECTOR_HASHER_MEMORY_COST,
    COLLECTOR_HASHER_PARALLELISM,
    COLLECTOR_HASHER_TYPE,
)

__all__ = ["hash_manager", "collector_hash_manager", "HashManager"]


class HashManager:
    def __init__(
        self,
        time_cost: int | None = None,
        memory_cost: int | None = None,
        parallelism: int | None = None,
        hash_type: Type | None = None,
    ) -> None:
        if time_cost is None:
            time_cost = DEFAULT_TIME_COST
        if memory_cost is None:
            memory_cost = DEFAULT_MEMORY_COST
        if parallelism is None:
            parallelism = DEFAULT_PARALLELISM
        if hash_type is None:
            hash_type = Type.ID

        self._hasher = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            type=hash_type,
        )

    def verify_hash(self, plain_value: str, hashed_value: str) -> bool:
        try:
            self._hasher.verify(hashed_value, plain_value)
            return True
        except VerifyMismatchError, InvalidHash:
            return False

    def get_hash(self, value: str) -> str:
        return self._hasher.hash(value)


hash_manager = HashManager()
collector_hash_manager = HashManager(
    time_cost=COLLECTOR_HASHER_TIME_COST,
    memory_cost=COLLECTOR_HASHER_MEMORY_COST,
    parallelism=COLLECTOR_HASHER_PARALLELISM,
    hash_type=COLLECTOR_HASHER_TYPE,
)
