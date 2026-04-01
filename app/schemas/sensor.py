from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums import SensorDataTypeEnum
from app.schemas.base import IdBase, CreatedAtBase
from app.schemas.reading import ReadingsBucketedResponse

__all__ = [
    "SensorBase",
    "SensorCreateRequest",
    "SensorUpdateRequest",
    "SensorControlRequest",
    "SensorResponse",
    "SensorWithReadingsResponse",
]


class SensorBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None
    node_id: str = Field(..., max_length=255)
    data_type: SensorDataTypeEnum = SensorDataTypeEnum.numeric
    units: str | None = Field(None, max_length=50)
    is_writable: bool = False


class SensorCreateRequest(SensorBase):
    opc_server_id: UUID


class SensorUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    node_id: str | None = Field(None, max_length=255)
    data_type: SensorDataTypeEnum | None = None
    units: str | None = Field(None, max_length=50)
    is_writable: bool | None = None


class SensorControlRequest(BaseModel):
    value: bool | int | float | str = Field(..., description="The new setpoint value for the sensor")


class SensorResponse(IdBase, CreatedAtBase):
    opc_server_id: UUID
    name: str
    description: str | None
    node_id: str
    data_type: SensorDataTypeEnum
    units: str | None
    is_writable: bool

    model_config = ConfigDict(from_attributes=True)


class SensorWithReadingsResponse(SensorResponse):
    readings: ReadingsBucketedResponse | None = None
