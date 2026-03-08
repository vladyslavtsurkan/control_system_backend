from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.enums import AlertSeverityEnum, AlertConditionEnum
from app.schemas.base import IdBase, CreatedAtBase

__all__ = [
    "AlertRuleBase",
    "AlertRuleCreateRequest",
    "AlertRuleUpdateRequest",
    "AlertRuleResponse",
]


class AlertRuleBase(BaseModel):
    name: str = Field(..., max_length=255)
    severity: AlertSeverityEnum = AlertSeverityEnum.WARNING
    condition: AlertConditionEnum
    threshold: dict[str, Any] = Field(
        ...,
        description='Target values, e.g. {"value": 100} or {"min": 20, "max": 50}',
    )


class AlertRuleCreateRequest(AlertRuleBase):
    sensor_id: UUID


class AlertRuleUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=255)
    severity: AlertSeverityEnum | None = None
    condition: AlertConditionEnum | None = None
    threshold: dict[str, Any] | None = None
    is_active: bool | None = None


class AlertRuleResponse(IdBase, CreatedAtBase):
    sensor_id: UUID
    name: str
    severity: AlertSeverityEnum
    condition: AlertConditionEnum
    threshold: dict[str, Any]
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
