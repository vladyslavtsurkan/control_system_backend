from app.schemas.base import PaginatedResponse
from app.schemas.auth import (
    SignUpRequest,
    SignUpResponse,
    SignUpVerifyRequest,
    SignUpVerifyResponse,
    LoginRequest,
    LoginResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    RefreshTokenRequest,
)
from app.schemas.user import UserBase, UserResponse, UserWithCreds, UserUpdateRequest
from app.schemas.organization import (
    OrganizationBase,
    OrganizationCreateRequest,
    OrganizationUpdateRequest,
    OrganizationResponse,
    OrganizationWithRoleResponse,
    OrganizationMemberResponse,
    ChangeRoleRequest,
)
from app.schemas.opc_server import (
    OpcServerBase,
    OpcServerCreateRequest,
    OpcServerUpdateRequest,
    OpcServerResponse,
)
from app.schemas.sensor import (
    SensorBase,
    SensorCreateRequest,
    SensorUpdateRequest,
    SensorResponse,
)
from app.schemas.reading import (
    ReadingResponse,
    AlertResponse,
)

__all__ = [
    # Base
    "PaginatedResponse",
    # Auth
    "SignUpResponse",
    "SignUpRequest",
    "SignUpVerifyRequest",
    "SignUpVerifyResponse",
    "LoginRequest",
    "LoginResponse",
    "ResetPasswordRequest",
    "ResetPasswordResponse",
    "ForgotPasswordRequest",
    "ForgotPasswordResponse",
    "RefreshTokenRequest",
    # User
    "UserBase",
    "UserResponse",
    "UserWithCreds",
    "UserUpdateRequest",
    # Organization
    "OrganizationBase",
    "OrganizationCreateRequest",
    "OrganizationUpdateRequest",
    "OrganizationResponse",
    "OrganizationWithRoleResponse",
    "OrganizationMemberResponse",
    "ChangeRoleRequest",
    # OPC Server
    "OpcServerBase",
    "OpcServerCreateRequest",
    "OpcServerUpdateRequest",
    "OpcServerResponse",
    # Sensor
    "SensorBase",
    "SensorCreateRequest",
    "SensorUpdateRequest",
    "SensorResponse",
    # Reading & Alert
    "ReadingResponse",
    "AlertResponse",
]
