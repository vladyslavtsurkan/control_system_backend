from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums import AuthMethodEnum, SecurityPolicyEnum
from app.schemas.base import IdBase, CreatedAtBase

__all__ = [
    "OpcServerBase",
    "OpcServerCreateRequest",
    "OpcServerUpdateRequest",
    "OpcServerResponse",
]


class OpcServerBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None
    url: str = Field(..., max_length=512)
    security_policy: SecurityPolicyEnum = SecurityPolicyEnum.NONE
    authentication_method: AuthMethodEnum = AuthMethodEnum.ANONYMOUS
    username: str | None = Field(None, max_length=255)
    password: str | None = Field(None, max_length=255, exclude=True)


class OpcServerCreateRequest(OpcServerBase):
    pass


class OpcServerUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    url: str | None = Field(None, max_length=512)
    security_policy: SecurityPolicyEnum | None = None
    authentication_method: AuthMethodEnum | None = None
    username: str | None = Field(None, max_length=255)
    password: str | None = Field(None, max_length=255, exclude=True)


class OpcServerResponse(IdBase, CreatedAtBase):
    organization_id: UUID
    name: str
    description: str | None
    url: str
    security_policy: SecurityPolicyEnum
    authentication_method: AuthMethodEnum
    username: str | None

    model_config = ConfigDict(from_attributes=True)
