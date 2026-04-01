from typing import Literal

from pydantic import Field

from app.core.config.base import BaseConfig

__all__ = ["RabbitMQConfig"]


class RabbitMQConfig(BaseConfig):
    HOST: str = Field(..., alias="RABBITMQ_HOST")
    PORT: int = Field(5672, alias="RABBITMQ_PORT")
    USER: str = Field(..., alias="RABBITMQ_USER")
    PASSWORD: str = Field(..., alias="RABBITMQ_PASSWORD")

    TELEMETRY_EXCHANGE: str = Field("iiot_telemetry", alias="RABBITMQ_TELEMETRY_EXCHANGE")
    TELEMETRY_QUEUE: str = Field("stream_processing", alias="RABBITMQ_TELEMETRY_QUEUE")
    TELEMETRY_ROUTING_KEY: str = Field("telemetry", alias="RABBITMQ_TELEMETRY_ROUTING_KEY")

    CONTROL_EXCHANGE: str = Field("iiot_control", alias="RABBITMQ_CONTROL_EXCHANGE")
    CONTROL_COMMAND_EXCHANGE: str = Field("iiot_control_command", alias="RABBITMQ_CONTROL_COMMAND_EXCHANGE")
    CONTROL_QUEUE: str = Field("rule_invalidation", alias="RABBITMQ_CONTROL_QUEUE")
    CONTROL_QUEUE_MODE: Literal["shared", "per_worker"] = Field(
        "per_worker",
        alias="RABBITMQ_CONTROL_QUEUE_MODE",
    )
    CONTROL_QUEUE_PREFIX: str = Field(
        "rule_invalidation",
        alias="RABBITMQ_CONTROL_QUEUE_PREFIX",
    )

    WS_BROADCAST_EXCHANGE: str = Field("ws_broadcast", alias="RABBITMQ_WS_BROADCAST_EXCHANGE")

    PREFETCH_COUNT: int = Field(20, alias="RABBITMQ_PREFETCH_COUNT")
    NO_DATA_CHECK_INTERVAL_SECONDS: int = Field(60, alias="RABBITMQ_NO_DATA_CHECK_INTERVAL_SECONDS")

    @property
    def url(self) -> str:
        return f"amqp://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/"
