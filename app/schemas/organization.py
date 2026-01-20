from pydantic import BaseModel, Field

from app.enums import UserRoleInOrgEnum
from app.schemas.base import IdBase, CreatedAtBase

__all__ = [
    "OrganizationBase",
    "OrganizationCreateRequest",
    "OrganizationUpdateRequest",
    "OrganizationResponse",
    "OrganizationWithRoleResponse",
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
    class Config:
        from_attributes = True


class OrganizationWithRoleResponse(OrganizationResponse):
    role: UserRoleInOrgEnum

    class Config:
        from_attributes = True
