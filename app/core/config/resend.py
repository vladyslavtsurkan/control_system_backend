from pydantic import Field

from app.core.config.base import BaseConfig


class ResendConfig(BaseConfig):
    API_URL: str = Field(..., alias="RESEND_API_URL")
    API_KEY: str = Field(..., alias="RESEND_API_KEY")
    FROM_EMAIL: str = Field(..., alias="RESEND_FROM_EMAIL")
