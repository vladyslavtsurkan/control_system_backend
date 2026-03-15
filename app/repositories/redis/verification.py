from app.core import settings
from app.repositories.redis.base import BaseRedisRepository
from app.schemas import UserWithCreds

OTP_VERIFIED_KEY = "verification:otp_verified:{email}"
OTP_FORGOT_PASSWORD_KEY = "verification:otp_forgot_password:{email}"


class VerificationRepository(BaseRedisRepository):
    DEFAULT_TTL_SECONDS = settings.auth.VERIFICATION_EXPIRE_MINUTES * 60

    async def create_verification(self, data: UserWithCreds, code: str) -> None:
        full_key = OTP_VERIFIED_KEY.format(email=data.email)
        data_dict = data.model_dump(mode="json")
        for key, value in data_dict.items():
            if isinstance(value, bool):
                data_dict[key] = int(value)
            elif value is None:
                data_dict[key] = ""
        data_dict["code"] = code
        await self.set(key=full_key, value=data_dict)

    async def get_verification(self, email: str, code: str) -> UserWithCreds | None:
        key = OTP_VERIFIED_KEY.format(email=email)
        item = await self.get(key=key)
        if not item or item.get("code") != code:
            return None
        item.pop("code", None)
        # Convert empty strings back to None for optional fields
        item = {k: (None if v == "" else v) for k, v in item.items()}
        return UserWithCreds(**item)

    async def check_verification(self, email: str) -> bool:
        key = OTP_VERIFIED_KEY.format(email=email)
        item = await self.get(key=key)
        return bool(item)

    async def delete_verification(self, email: str) -> None:
        key = OTP_VERIFIED_KEY.format(email=email)
        await self.delete(key=key)

    async def create_forgot_password_otp(self, email: str, code: str) -> None:
        full_key = OTP_FORGOT_PASSWORD_KEY.format(email=email)
        await self.set(key=full_key, value={"code": code})

    async def get_forgot_password_otp(self, email: str, code: str) -> bool:
        key = OTP_FORGOT_PASSWORD_KEY.format(email=email)
        item = await self.get(key=key)
        if not item or item.get("code") != code:
            return False
        return True

    async def check_forgot_password_otp(self, email: str) -> bool:
        key = OTP_FORGOT_PASSWORD_KEY.format(email=email)
        item = await self.get(key=key)
        return bool(item)

    async def delete_forgot_password_otp(self, email: str) -> None:
        key = OTP_FORGOT_PASSWORD_KEY.format(email=email)
        await self.delete(key=key)
