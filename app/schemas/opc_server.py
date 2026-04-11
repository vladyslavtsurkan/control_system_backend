from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums import AuthMethodEnum, SecurityPolicyEnum
from app.schemas.base import IdBase, CreatedAtBase

__all__ = [
    "OpcServerBase",
    "OpcServerCreateRequest",
    "OpcServerUpdateRequest",
    "OpcServerResponse",
    "ApiKeyCreateResponse",
    "ApiKeyInfoResponse",
]


class OpcServerBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None
    url: str = Field(..., max_length=512)
    security_policy: SecurityPolicyEnum = SecurityPolicyEnum.none
    authentication_method: AuthMethodEnum = AuthMethodEnum.anonymous
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


class ApiKeyCreateResponse(BaseModel):
    key_id: str = Field(..., description="Public API key identifier. Send as X-API-Key-ID header.")
    secret_key: str = Field(..., description="The API key secret. Shown only once. Send as X-API-Key-Secret header.")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApiKeyInfoResponse(IdBase, CreatedAtBase):
    opc_server_id: UUID
    key_id: str
    last_used_at: datetime | None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
