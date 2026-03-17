from app.enums.base import BaseStrEnum

__all__ = ["SensorDataTypeEnum"]


class SensorDataTypeEnum(BaseStrEnum):
    """Enum representing sensor telemetry value types."""

    numeric = "numeric"
    boolean = "boolean"
    string = "string"
