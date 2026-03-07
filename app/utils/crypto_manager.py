from cryptography.fernet import Fernet

from app.core.config import settings

__all__ = ["crypto_manager", "CryptoManager"]


class CryptoManager:
    """Symmetric encryption manager using Fernet (AES-128-CBC + HMAC-SHA256)."""

    def __init__(self, key: str):
        self._fernet = Fernet(key.encode())

    def encrypt(self, plain_text: str) -> str:
        """Encrypt a plaintext string and return a URL-safe base64-encoded token."""
        return self._fernet.encrypt(plain_text.encode()).decode()

    def decrypt(self, cipher_text: str) -> str:
        """Decrypt a Fernet token back to the original plaintext string."""
        return self._fernet.decrypt(cipher_text.encode()).decode()


crypto_manager = CryptoManager(settings.encryption.KEY)
