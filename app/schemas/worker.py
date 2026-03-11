from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

__all__ = ["TelemetryPayload", "TelemetryReading"]


class TelemetryPayload(BaseModel):
    value: float
    status: str


class TelemetryReading(BaseModel):
    sensor_id: UUID
    time: datetime
    payload: TelemetryPayload
