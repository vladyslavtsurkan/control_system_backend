from datetime import datetime
from typing import Any, Literal, TypedDict
from uuid import UUID

__all__ = ["ReadingWrite", "AlertEvent"]


class ReadingWrite(TypedDict):
    time: datetime
    organization_id: UUID | None
    sensor_id: UUID
    val_num: float | None
    val_bool: bool | None
    val_str: str | None
    payload: dict[str, Any]


class AlertEvent(TypedDict):
    sensor_id: UUID
    rule_id: UUID
    severity: str
    message: str
    triggered_value: dict[str, Any]
    action: Literal["open", "update", "resolve"]
