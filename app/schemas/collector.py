from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.enums import AuthMethodEnum, SecurityPolicyEnum, SensorDataTypeEnum

__all__ = [
    "CollectorSensorResponse",
    "CollectorConfigResponse",
]


class CollectorSensorResponse(BaseModel):
    id: UUID
    name: str
    node_id: str
    data_type: SensorDataTypeEnum
    units: str | None

    model_config = ConfigDict(from_attributes=True)


class CollectorConfigResponse(BaseModel):
    id: UUID
    name: str
    url: str
    security_policy: SecurityPolicyEnum
    authentication_method: AuthMethodEnum
    username: str | None
    password: str | None
    sensors: list[CollectorSensorResponse]

    model_config = ConfigDict(from_attributes=True)
