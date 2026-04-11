import secrets

from app.core.constants import API_KEY_LENGTH, API_KEY_ID_BYTES
from app.utils.hash_manager import collector_hash_manager

__all__ = ["api_key_manager", "ApiKeyManager"]


class ApiKeyManager:
    """Manager for generating, hashing, and verifying collector API keys."""

    @staticmethod
    def generate(length: int = API_KEY_LENGTH) -> tuple[str, str, str]:
        """
        Generate a new API key.

        Returns:
            A tuple of (key_id, secret_key, hashed_secret).
            - key_id:      random hex identifier (32 chars) stored in DB and sent as X-API-Key-ID.
            - secret_key:  plaintext secret returned to the user once; sent as X-API-Key-Secret.
            - hashed_secret: Argon2 hash of secret_key persisted in the database.
        """
        key_id = secrets.token_hex(API_KEY_ID_BYTES)
        secret_key = secrets.token_urlsafe(length)
        hashed_secret = collector_hash_manager.get_hash(secret_key)
        return key_id, secret_key, hashed_secret

    @staticmethod
    def verify(plain_secret: str, hashed_secret: str) -> bool:
        """Verify a plain API secret against its stored hash."""
        return collector_hash_manager.verify_hash(plain_secret, hashed_secret)


api_key_manager = ApiKeyManager()
