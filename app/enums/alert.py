from app.enums.base import BaseStrEnum

__all__ = ["AlertSeverityEnum", "AlertConditionEnum"]


class AlertSeverityEnum(BaseStrEnum):
    """
    Enum representing alert severity levels.
    """

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    FATAL = "fatal"


class AlertConditionEnum(BaseStrEnum):
    """
    Enum representing alert condition types.
    """

    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    OUTSIDE_RANGE = "outside_range"
    INSIDE_RANGE = "inside_range"
    NO_DATA = "no_data"
