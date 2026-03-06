from pydantic import BaseModel, ConfigDict, Field

from app.enums import UserRoleInOrgEnum
from app.schemas.base import IdBase, CreatedAtBase
from app.schemas.user import UserResponse

__all__ = [
    "OrganizationBase",
    "OrganizationCreateRequest",
    "OrganizationUpdateRequest",
    "OrganizationResponse",
    "OrganizationWithRoleResponse",
    "OrganizationMemberResponse",
    "ChangeRoleRequest",
]


class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class OrganizationCreateRequest(OrganizationBase):
    pass


class OrganizationUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class OrganizationResponse(IdBase, OrganizationBase, CreatedAtBase):
    model_config = ConfigDict(from_attributes=True)


class OrganizationWithRoleResponse(OrganizationResponse):
    role: UserRoleInOrgEnum

    model_config = ConfigDict(from_attributes=True)


class OrganizationMemberResponse(UserResponse):
    role: UserRoleInOrgEnum


class ChangeRoleRequest(BaseModel):
    role: UserRoleInOrgEnum
