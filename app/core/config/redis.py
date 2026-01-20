from pydantic import Field

from app.core.config.base import BaseConfig


class RedisConfig(BaseConfig):
    HOST: str = Field(..., alias="REDIS_HOST")
    PORT: int = Field(..., alias="REDIS_PORT")
    PASSWORD: str | None = Field(None, alias="REDIS_PASSWORD")
    DB: int = Field(0, alias="REDIS_DB")
    MAX_CONNECTIONS: int = Field(10, alias="REDIS_MAX_CONNECTIONS")

    @property
    def url(self) -> str:
        """Constructs the Redis URL using the Redis configuration."""
        if self.PASSWORD:
            return f"redis://:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.DB}"
        return f"redis://{self.HOST}:{self.PORT}/{self.DB}"
