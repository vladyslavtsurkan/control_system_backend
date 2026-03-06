from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash

__all__ = ["hash_manager", "HashManager"]


class HashManager:
    def __init__(self):
        self._hasher = PasswordHasher()

    def verify_hash(self, plain_value: str, hashed_value: str) -> bool:
        try:
            self._hasher.verify(hashed_value, plain_value)
            return True
        except VerifyMismatchError, InvalidHash:
            return False

    def get_hash(self, value: str) -> str:
        return self._hasher.hash(value)


hash_manager = HashManager()
