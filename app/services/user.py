import uuid

from loguru import logger

from app.core import settings
from app.core.exc import (
    UserAlreadyExistsException,
    VerificationCodeAlreadySentException,
    VerificationFailedOrExpiredException,
)
from app.schemas import (
    SignUpRequest,
    UserWithCreds,
    SignUpResponse,
    SignUpVerifyRequest,
    SignUpVerifyResponse,
    UserResponse,
    UserUpdateRequest,
)
from app.services.auth import AuthService
from app.services.resend import resend_service
from app.uow.redis import RedisUnitOfWork
from app.uow.sql import SQLUnitOfWork
from app.utils.hash_manager import hash_manager
from app.utils.helpers import generate_code


class UserService:
    def __init__(self) -> None:
        self._hash_manager = hash_manager
        self._config = settings.auth
        self._email_service = resend_service
        self._auth_service = AuthService()

    async def signup(self, uow: SQLUnitOfWork, request: SignUpRequest) -> SignUpResponse:
        async with uow:
            if await uow.user.count({"email": request.email}):
                raise UserAlreadyExistsException(str(request.email))

        request_dict = request.model_dump()
        hashed_password = self._hash_manager.get_hash(request_dict.pop("password"))
        user = UserWithCreds(id=uuid.uuid7(), hashed_password=hashed_password, is_active=True, **request_dict)
        code = generate_code()

        async with RedisUnitOfWork() as redis_uow:
            if await redis_uow.verification.check_verification(email=user.email):
                raise VerificationCodeAlreadySentException(str(user.email))
            await redis_uow.verification.create_verification(data=user, code=code)
        await self._email_service.send_verification_code_email(recipient=user.email, code=code)
        logger.info(f"Verification code sent to: {user.email}")

        return SignUpResponse(message="User created successfully. Please verify your email to activate your account.")

    async def signup_verify(self, uow: SQLUnitOfWork, request: SignUpVerifyRequest) -> SignUpVerifyResponse:
        async with RedisUnitOfWork() as redis_uow:
            verification = await redis_uow.verification.get_verification(email=request.email, code=request.code)
            if not verification:
                raise VerificationFailedOrExpiredException(str(request.email))

            await redis_uow.verification.delete_verification(email=request.email)

        async with uow:
            await uow.user.create(verification.model_dump())

        logger.info(f"User verified and created: {request.email}")
        email = str(request.email)

        return SignUpVerifyResponse(
            access_token=self._auth_service.create_access_token(email),
            refresh_token=self._auth_service.create_refresh_token(email),
        )

    @staticmethod
    async def update_user(uow: SQLUnitOfWork, current_user: UserResponse, request: UserUpdateRequest) -> UserResponse:
        async with uow:
            user = await uow.user.update(
                filters={"id": current_user.id}, updates=request.model_dump(exclude_unset=True)
            )
            return UserResponse.model_validate(user)
