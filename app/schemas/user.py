from pydantic import EmailStr, BaseModel

from app.schemas.base import IdBase, TimestampBase

__all__ = ["UserBase", "UserResponse", "UserWithCreds", "UserUpdateRequest"]


class UserBase(BaseModel):
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None


class UserResponse(IdBase, TimestampBase, UserBase):
    class Config:
        from_attributes = True


class UserWithCreds(IdBase, UserBase):
    hashed_password: str
    is_active: bool

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
