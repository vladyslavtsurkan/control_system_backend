from app.core.config.base import BaseConfig
from app.core.config.db import DataBaseConfig
from app.core.config.auth import AuthConfig
from app.core.config.swagger import SwaggerConfig

__all__ = ["Settings", "settings"]


class Settings(BaseConfig):
    SERVER_HOST: str
    SERVER_PORT: int
    RELOAD: bool = False

    FRONTEND_URL: list[str]

    db: DataBaseConfig = DataBaseConfig()
    auth: AuthConfig = AuthConfig()
    swagger: SwaggerConfig = SwaggerConfig()


settings = Settings()
