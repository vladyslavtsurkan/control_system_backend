import secrets

from app.core.constants import API_KEY_LENGTH, API_KEY_PREFIX
from app.utils.hash_manager import collector_hash_manager

__all__ = ["api_key_manager", "ApiKeyManager"]


class ApiKeyManager:
    """Manager for generating, hashing, and verifying collector API keys."""

    @staticmethod
    def generate(length: int = API_KEY_LENGTH) -> tuple[str, str, str]:
        """
        Generate a new API key.

        Returns:
            A tuple of (full_key, key_prefix, hashed_key).
            - full_key: the plaintext secret to return to the user once.
            - key_prefix: a truncated display string, e.g. "sk_live_a1b2c3d4...".
            - hashed_key: the Argon2 hash to persist in the database.
        """
        raw_key = secrets.token_urlsafe(length)
        full_key = f"{API_KEY_PREFIX}{raw_key}"
        key_prefix = f"{API_KEY_PREFIX}{raw_key[:8]}..."
        hashed_key = collector_hash_manager.get_hash(full_key)
        return full_key, key_prefix, hashed_key

    @staticmethod
    def verify(plain_key: str, hashed_key: str) -> bool:
        """Verify a plain API key against its stored hash."""
        return collector_hash_manager.verify_hash(plain_key, hashed_key)


api_key_manager = ApiKeyManager()
