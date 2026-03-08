from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt, ExpiredSignatureError

from app.core import settings
from app.core.exc import (
    BadRequestException,
    TokenRefreshException,
    UserNotFoundException,
    InvalidCredentialsException,
    PasswordInvalidException,
    ForgotPasswordCodeAlreadySentException,
    ForgotPasswordCodeFailedOrExpiredException,
)
from app.enums import MessageException
from app.models import User
from app.schemas import (
    UserResponse,
    LoginResponse,
    ForgotPasswordResponse,
    ResetPasswordResponse,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.schemas.auth import RefreshTokenRequest
from app.services.resend import resend_service
from app.uow.redis import RedisUnitOfWork
from app.uow.sql import SQLUnitOfWork
from app.utils.auth_manager import AuthManager
from app.utils.hash_manager import hash_manager
from app.utils.token_manager import jwt_token_manager
from app.utils.utils import generate_code

http_bearer = HTTPBearer()


class AuthService:
    def __init__(self):
        self._config = settings.auth
        self._hash_manager = hash_manager
        self._email_service = resend_service

    async def authenticate_user(self, email: str, uow: SQLUnitOfWork, password: str) -> UserResponse:
        async with uow:
            user = await uow.user.get(filters={"email": email})

            if not user:
                raise UserNotFoundException(email)

            AuthManager.ensure_active(user)

            if not self._hash_manager.verify_hash(password, user.hashed_password):
                raise PasswordInvalidException

            return user

    async def login(self, uow: SQLUnitOfWork, request: LoginRequest) -> LoginResponse:
        email = str(request.email)

        await self.authenticate_user(email, uow=uow, password=request.password)

        return LoginResponse(
            access_token=self.create_access_token(email), refresh_token=self.create_refresh_token(email)
        )

    async def forgot_password(self, uow: SQLUnitOfWork, request: ForgotPasswordRequest) -> ForgotPasswordResponse:
        email = str(request.email)
        async with uow:
            user = await uow.user.get(filters={"email": email})

            self._validate_user(user)

        async with RedisUnitOfWork() as redis_uow:
            if await redis_uow.verification.check_forgot_password_otp(email):
                raise ForgotPasswordCodeAlreadySentException(email)

            code = generate_code()

            await redis_uow.verification.create_forgot_password_otp(email, code)

        await self._email_service.send_reset_password_email(recipient=email, code=code)

        return ForgotPasswordResponse(message="Password reset code sent to your email.")

    async def reset_password(self, uow: SQLUnitOfWork, request: ResetPasswordRequest) -> ResetPasswordResponse:
        email = str(request.email)
        async with uow:
            user = await uow.user.get(filters={"email": email})

            if user is None:
                raise UserNotFoundException(email)

            AuthManager.ensure_active(user)

            async with RedisUnitOfWork() as redis_uow:
                if not await redis_uow.verification.get_forgot_password_otp(email, request.code):
                    raise ForgotPasswordCodeFailedOrExpiredException(email)

                if self._hash_manager.verify_hash(request.password, user.hashed_password):
                    raise BadRequestException(MessageException.password_same_as_old)

                await redis_uow.verification.delete_forgot_password_otp(email)

            await uow.user.update(
                filters={"email": email}, updates={"hashed_password": hash_manager.get_hash(request.password)}
            )

        return ResetPasswordResponse(message="Password reset successful")

    @staticmethod
    def create_access_token(email: str) -> str:
        data = {"sub": email, "type": "access"}
        return jwt_token_manager.create_access_token(data)

    @staticmethod
    def create_refresh_token(email: str) -> str:
        data = {"sub": email, "type": "refresh"}
        return jwt_token_manager.create_refresh_token(data)

    @classmethod
    async def refresh_access_token(cls, uow: SQLUnitOfWork, request: RefreshTokenRequest) -> LoginResponse:
        payload = jwt_token_manager.decode_token(request.refresh_token)
        if payload.get("type", "") != "refresh":
            raise TokenRefreshException

        email = payload.get("sub")

        async with uow:
            user = await uow.user.get(filters={"email": email})

        if user is None:
            raise TokenRefreshException

        try:
            new_access_token, new_refresh_token = (
                cls.create_access_token(email),
                cls.create_refresh_token(email),
            )
        except JWTError, KeyError:
            raise TokenRefreshException

        return LoginResponse(access_token=new_access_token, refresh_token=new_refresh_token)

    @staticmethod
    async def __check_own_token(token: str) -> str:
        payload = jwt_token_manager.decode_token(token)
        if payload:
            if payload.get("type", "") != "access":
                raise InvalidCredentialsException
            return payload.get("sub")
        raise InvalidCredentialsException

    @classmethod
    async def get_current_user(
        cls, token: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())]
    ) -> UserResponse:
        try:
            jwt.decode(
                token.credentials,
                options={"verify_signature": False, "verify_aud": False, "verify_at_hash": False},
                key="",
            )
        except ExpiredSignatureError:
            raise InvalidCredentialsException

        try:
            email = await cls.__check_own_token(token.credentials)

            async with SQLUnitOfWork() as uow:
                user = await uow.user.get(filters={"email": email})

                cls._validate_user(user)

                return UserResponse.model_validate(user)

        except JWTError, KeyError:
            raise InvalidCredentialsException

    @staticmethod
    def _validate_user(user: User | None) -> None:
        if not user:
            raise UserNotFoundException("Unknown")

        AuthManager.ensure_active(user)


auth_service = AuthService()
