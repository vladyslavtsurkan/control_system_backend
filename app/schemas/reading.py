from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.alert_rule import AlertRuleBriefResponse
from app.schemas.base import IdBase, CreatedAtBase

__all__ = [
    "ReadingResponse",
    "ReadingsBucketedResponse",
    "AlertResponse",
]


class ReadingResponse(BaseModel):
    sensor_id: UUID
    payload: dict[str, Any]
    time: datetime

    model_config = ConfigDict(from_attributes=True)


class ReadingsBucketedResponse(BaseModel):
    times: list[str]
    values: list[float]


class AlertResponse(IdBase, CreatedAtBase):
    sensor_id: UUID
    rule: AlertRuleBriefResponse | None = None
    message: str
    triggered_value: dict[str, Any]
    is_acknowledged: bool
    resolved_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
