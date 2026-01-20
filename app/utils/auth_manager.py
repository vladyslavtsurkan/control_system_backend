from app.core.exc import UserDeactivatedException
from app.models import User


class AuthManager:
    @staticmethod
    def ensure_active(user: User):
        if not user.is_active:
            raise UserDeactivatedException
