from pydantic import Field

from app.core.config.base import BaseConfig


class AuthConfig(BaseConfig):
    SECRET_KEY: str = Field(..., alias="AUTH_SECRET_KEY")
    ALGORITHM: str = Field("HS256", alias="AUTH_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_HOURS: int = Field(24, alias="AUTH_ACCESS_TOKEN_EXPIRE_HOURS")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(14, alias="AUTH_REFRESH_TOKEN_EXPIRE_DAYS")
    VERIFICATION_EXPIRE_MINUTES: int = Field(60, alias="AUTH_VERIFICATION_EXPIRE_MINUTES")
