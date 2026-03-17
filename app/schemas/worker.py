from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, StrictBool, StrictFloat, StrictInt, StrictStr

__all__ = ["TelemetryPayload", "TelemetryReading"]


class TelemetryPayload(BaseModel):
    value: StrictBool | StrictInt | StrictFloat | StrictStr
    status: str


class TelemetryReading(BaseModel):
    sensor_id: UUID
    time: datetime
    payload: TelemetryPayload
