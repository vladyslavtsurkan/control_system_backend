from app.core.config.base import BaseConfig
from app.core.config.db import DataBaseConfig
from app.core.config.auth import AuthConfig
from app.core.config.encryption import EncryptionConfig
from app.core.config.redis import RedisConfig
from app.core.config.resend import ResendConfig
from app.core.config.swagger import SwaggerConfig
from app.core.config.rabbitmq import RabbitMQConfig
from app.core.config.worker import WorkerConfig

__all__ = ["Settings", "settings"]


class Settings(BaseConfig):
    IS_PRODUCTION: bool = False

    SERVER_HOST: str
    SERVER_PORT: int
    RELOAD: bool = False

    FRONTEND_URL: list[str]

    db: DataBaseConfig = DataBaseConfig()
    auth: AuthConfig = AuthConfig()
    encryption: EncryptionConfig = EncryptionConfig()
    swagger: SwaggerConfig = SwaggerConfig()
    resend: ResendConfig = ResendConfig()
    redis: RedisConfig = RedisConfig()
    rabbitmq: RabbitMQConfig = RabbitMQConfig()
    worker: WorkerConfig = WorkerConfig()


settings = Settings()
