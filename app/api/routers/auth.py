from fastapi import APIRouter, status

from app.api.dependencies import SQLUnitOfWorkDep, user_service, auth_service
from app.schemas import (
    SignUpResponse,
    SignUpRequest,
    SignUpVerifyRequest,
    SignUpVerifyResponse,
    LoginRequest,
    LoginResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    RefreshTokenRequest,
)

__all__ = ["router"]

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", response_model=SignUpResponse, status_code=status.HTTP_200_OK)
async def signup(request: SignUpRequest, uow: SQLUnitOfWorkDep, service: user_service):
    """Sign up a new user. This will send a verification code to the user's email."""
    return await service.signup(request=request, uow=uow)


@router.post("/signup/verify", response_model=SignUpVerifyResponse, status_code=status.HTTP_201_CREATED)
async def signup_verify(request: SignUpVerifyRequest, uow: SQLUnitOfWorkDep, service: user_service):
    """Verify a user's email with the code sent to their email during signup."""
    return await service.signup_verify(request=request, uow=uow)


@router.post("/login", status_code=status.HTTP_200_OK, response_model=LoginResponse)
async def login(request: LoginRequest, uow: SQLUnitOfWorkDep, service: auth_service):
    """Authenticate a user and return access and refresh tokens."""
    return await service.login(uow=uow, request=request)


@router.post("/refresh-token", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def refresh_token(request: RefreshTokenRequest, uow: SQLUnitOfWorkDep, service: auth_service):
    """Refresh the access token using a valid refresh token."""
    return await service.refresh_access_token(uow=uow, request=request)


@router.post("/forgot-password", response_model=ForgotPasswordResponse, status_code=status.HTTP_200_OK)
async def forgot_password(request: ForgotPasswordRequest, uow: SQLUnitOfWorkDep, service: auth_service):
    """Initiate the forgot password process by sending a reset code to the user's email."""
    return await service.forgot_password(uow=uow, request=request)


@router.post("/reset-password", response_model=ResetPasswordResponse, status_code=status.HTTP_200_OK)
async def reset_password(request: ResetPasswordRequest, uow: SQLUnitOfWorkDep, service: auth_service):
    """Reset the user's password using the code sent to their email during the forgot password process."""
    return await service.reset_password(uow=uow, request=request)
