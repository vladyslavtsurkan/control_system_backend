from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.base import IdBase, CreatedAtBase

__all__ = [
    "ReadingResponse",
    "AlertResponse",
]


class ReadingResponse(BaseModel):
    sensor_id: UUID
    value: float
    time: datetime

    class Config:
        from_attributes = True


class AlertResponse(IdBase, CreatedAtBase):
    sensor_id: UUID
    message: str
    triggered_value: float

    class Config:
        from_attributes = True
