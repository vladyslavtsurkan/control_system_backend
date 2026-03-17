from app.enums.base import BaseStrEnum

__all__ = ["AlertSeverityEnum", "AlertConditionEnum"]


class AlertSeverityEnum(BaseStrEnum):
    """
    Enum representing alert severity levels.
    """

    info = "info"
    warning = "warning"
    critical = "critical"
    fatal = "fatal"


class AlertConditionEnum(BaseStrEnum):
    """
    Enum representing alert condition types.
    """

    greater_than = "greater_than"
    less_than = "less_than"
    equals = "equals"
    not_equals = "not_equals"
    outside_range = "outside_range"
    inside_range = "inside_range"
    no_data = "no_data"
