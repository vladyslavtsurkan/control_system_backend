from typing import Annotated, Any, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    model_validator,
    field_validator,
)

from app.core.constants import MAX_AMOUNT_OF_ACTIONS_PER_RULE
from app.enums import AlertSeverityEnum, AlertConditionEnum
from app.schemas.base import IdBase, CreatedAtBase

__all__ = [
    "SingleValueThreshold",
    "RangeThreshold",
    "NoDataThreshold",
    "Threshold",
    "AlertRuleBase",
    "AlertActionCreateRequest",
    "AlertActionResponse",
    "AlertRuleCreateRequest",
    "AlertRuleUpdateRequest",
    "AlertRuleBriefResponse",
    "AlertRuleResponse",
]

_SINGLE_VALUE_CONDITIONS: frozenset[AlertConditionEnum] = frozenset(
    {
        AlertConditionEnum.greater_than,
        AlertConditionEnum.less_than,
        AlertConditionEnum.equals,
        AlertConditionEnum.not_equals,
    }
)

_RANGE_CONDITIONS: frozenset[AlertConditionEnum] = frozenset(
    {
        AlertConditionEnum.outside_range,
        AlertConditionEnum.inside_range,
    }
)

_NO_DATA_CONDITIONS: frozenset[AlertConditionEnum] = frozenset(
    {
        AlertConditionEnum.no_data,
    }
)


class SingleValueThreshold(BaseModel):
    """Threshold for single-value conditions (greater_than, less_than, equals, not_equals)."""

    type: Literal["single_value"] = "single_value"
    value: StrictBool | StrictInt | StrictFloat | StrictStr


class RangeThreshold(BaseModel):
    """Threshold for range conditions (outside_range, inside_range)."""

    type: Literal["range"] = "range"
    min: float
    max: float

    @model_validator(mode="after")
    def _min_less_than_max(self) -> Self:
        if self.min >= self.max:
            raise ValueError("`min` must be less than `max`")
        return self


class NoDataThreshold(BaseModel):
    """Threshold for no_data condition – no numeric values required."""

    type: Literal["no_data"] = "no_data"
    timeout_seconds: int = 300


Threshold = Annotated[
    SingleValueThreshold | RangeThreshold | NoDataThreshold,
    Field(discriminator="type"),
]

_CONDITION_TO_THRESHOLD_TYPE: dict[AlertConditionEnum, str] = {
    **{c: "single_value" for c in _SINGLE_VALUE_CONDITIONS},
    **{c: "range" for c in _RANGE_CONDITIONS},
    **{c: "no_data" for c in _NO_DATA_CONDITIONS},
}


def _validate_condition_threshold(
    condition: AlertConditionEnum, threshold: SingleValueThreshold | RangeThreshold | NoDataThreshold
) -> None:
    expected = _CONDITION_TO_THRESHOLD_TYPE.get(condition)
    if expected and threshold.type != expected:
        raise ValueError(f"Condition `{condition.value}` requires threshold type `{expected}`, got `{threshold.type}`")

    if condition in {AlertConditionEnum.greater_than, AlertConditionEnum.less_than} and isinstance(
        threshold, SingleValueThreshold
    ):
        if isinstance(threshold.value, bool) or not isinstance(threshold.value, (int, float)):
            raise ValueError(f"Condition `{condition.value}` requires numeric `threshold.value`")


def _validate_alert_actions(actions: list[AlertActionCreateRequest]) -> None:
    if len(actions) > MAX_AMOUNT_OF_ACTIONS_PER_RULE:
        raise ValueError(f"A maximum of {MAX_AMOUNT_OF_ACTIONS_PER_RULE} actions are allowed per alert rule")


class AlertRuleBase(BaseModel):
    name: str = Field(..., max_length=255)
    severity: AlertSeverityEnum = AlertSeverityEnum.warning
    condition: AlertConditionEnum
    threshold: Threshold = Field(
        ...,
        description=(
            'Threshold parameters. Use {"type": "single_value", "value": 100} for '
            'comparison conditions, {"type": "range", "min": 20, "max": 50} for range '
            'conditions, or {"type": "no_data"} for no-data condition.'
        ),
    )
    duration_seconds: int = Field(0, ge=0)

    @model_validator(mode="after")
    def _check_condition_threshold(self) -> Self:
        _validate_condition_threshold(self.condition, self.threshold)
        return self


class AlertRuleCreateRequest(AlertRuleBase):
    sensor_id: UUID
    actions: list["AlertActionCreateRequest"] | None = None

    @field_validator("actions")
    @classmethod
    def _validate_actions(cls, value: list[AlertActionCreateRequest] | None) -> None:
        if value is not None:
            _validate_alert_actions(value)
        return value


class AlertRuleUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=255)
    severity: AlertSeverityEnum | None = None
    condition: AlertConditionEnum | None = None
    threshold: Threshold | None = None
    duration_seconds: int | None = Field(None, ge=0)
    is_active: bool | None = None
    actions: list["AlertActionCreateRequest"] | None = None

    @model_validator(mode="after")
    def _check_condition_threshold(self) -> Self:
        if self.condition is not None and self.threshold is not None:
            _validate_condition_threshold(self.condition, self.threshold)
        if self.actions is not None:
            _validate_alert_actions(self.actions)
        return self


class AlertRuleBriefResponse(IdBase, CreatedAtBase):
    sensor_id: UUID
    name: str
    severity: AlertSeverityEnum
    condition: AlertConditionEnum
    duration_seconds: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class AlertRuleResponse(IdBase, CreatedAtBase):
    sensor_id: UUID
    name: str
    severity: AlertSeverityEnum
    condition: AlertConditionEnum
    threshold: Threshold
    duration_seconds: int
    is_active: bool
    actions: list["AlertActionResponse"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AlertActionCreateRequest(BaseModel):
    target_sensor_id: UUID
    trigger_payload: dict[str, Any] | None = None
    resolve_payload: dict[str, Any] | None = None


class AlertActionResponse(IdBase, CreatedAtBase, AlertActionCreateRequest):
    rule_id: UUID

    model_config = ConfigDict(from_attributes=True)
