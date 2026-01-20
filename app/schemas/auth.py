import re

from pydantic import BaseModel, EmailStr, Field, field_validator

__all__ = [
    "SignUpRequest",
    "SignUpResponse",
    "SignUpVerifyRequest",
    "SignUpVerifyResponse",
    "LoginRequest",
    "LoginResponse",
    "RefreshTokenRequest",
    "ForgotPasswordRequest",
    "ForgotPasswordResponse",
    "ResetPasswordRequest",
    "ResetPasswordResponse",
]


class SignUpRequest(BaseModel):
    email: EmailStr
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    password: str = Field(..., min_length=8, max_length=64)

    @field_validator("email")
    @classmethod
    def email_validator(cls, email: str) -> str:
        return email.lower()

    @field_validator("password")
    @classmethod
    def password_validator(cls, password: str) -> str:
        pattern = r"^(?=.*?[A-Z])(?=.*?[a-z])(?=.*?[0-9]).{8,}$"
        if not bool(re.match(pattern, password)):
            raise ValueError(
                "Invalid password provided. Password must be at least 8 characters long, "
                "contain at least one uppercase letter, one lowercase letter, and one digit."
            )
        return password


class SignUpResponse(BaseModel):
    message: str


class SignUpVerifyRequest(BaseModel):
    email: EmailStr
    code: str

    @field_validator("email")
    @classmethod
    def email_validator(cls, email: str) -> str:
        return email.lower()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    refresh_token: str
    access_token: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class SignUpVerifyResponse(LoginResponse):
    pass


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    password: str = Field(..., min_length=8, max_length=64)

    @field_validator("password")
    @classmethod
    def password_validator(cls, password: str) -> str:
        pattern = r"^(?=.*?[A-Z])(?=.*?[a-z])(?=.*?[0-9]).{8,}$"
        if not bool(re.match(pattern, password)):
            raise ValueError(
                "Invalid password provided. Password must be at least 8 characters long, "
                "contain at least one uppercase letter, one lowercase letter, and one digit."
            )
        return password


class ResetPasswordResponse(BaseModel):
    message: str
