from pydantic import Field

from app.core.config.base import BaseConfig


class SwaggerConfig(BaseConfig):
    USERNAME: str = Field(..., alias="SWAGGER_USERNAME")
    PASSWORD: str = Field(..., alias="SWAGGER_PASSWORD")
