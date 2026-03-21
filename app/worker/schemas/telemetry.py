from datetime import datetime
from uuid import UUID
from typing import TypedDict

__all__ = ["TelemetryPayload", "TelemetryReading"]


class TelemetryPayload(TypedDict):
    value: bool | int | float | str
    status: str


class TelemetryReading(TypedDict):
    sensor_id: UUID
    time: datetime
    payload: TelemetryPayload
