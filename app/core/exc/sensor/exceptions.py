from uuid import UUID

from app.enums import MessageException
from app.core.exc.base.exceptions import BadRequestException


__all__ = ["SensorIsNotWritableException"]


class SensorIsNotWritableException(BadRequestException):
    """Exception raised when trying to write to a non-writable sensor."""

    def __init__(self, sensor_id: UUID) -> None:
        super().__init__(message=MessageException.sensor_is_not_writable)
        self.alias.update({"sensor_id": sensor_id})
