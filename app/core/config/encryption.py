from pydantic import Field

from app.core.config.base import BaseConfig

__all__ = ["EncryptionConfig"]


class EncryptionConfig(BaseConfig):
    KEY: str = Field(..., alias="ENCRYPTION_KEY")
