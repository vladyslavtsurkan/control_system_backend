from app.core.exc import ForbiddenException, NotAuthorizedException
from app.core.exc.base.exceptions import ObjectAlreadyExistsException, ObjectNotFoundException

__all__ = [
    "UserAlreadyExistsException",
    "VerificationCodeAlreadySentException",
    "VerificationFailedOrExpiredException",
    "InvalidCredentialsException",
    "TokenRefreshException",
    "UserDeactivatedException",
    "UserNotFoundException",
    "PasswordInvalidException",
    "ForgotPasswordCodeAlreadySentException",
    "ForgotPasswordCodeFailedOrExpiredException",
]

from app.enums import MessageException


class UserAlreadyExistsException(ObjectAlreadyExistsException):
    def __init__(self, email: str) -> None:
        super().__init__(id_=email, model_name="User")


class VerificationCodeAlreadySentException(ObjectAlreadyExistsException):
    def __init__(self, email: str) -> None:
        super().__init__(id_=email, model_name="VerificationCode")


class VerificationFailedOrExpiredException(ObjectNotFoundException):
    def __init__(self, email: str) -> None:
        super().__init__(id_=email, model_name="VerificationCode")
        self.message = MessageException.verification_failed_or_expired


class InvalidCredentialsException(NotAuthorizedException):
    def __init__(self) -> None:
        super().__init__(MessageException.could_not_validate_credentials)


class TokenRefreshException(ForbiddenException):
    def __init__(self) -> None:
        super().__init__(MessageException.could_not_refresh_token)


class UserDeactivatedException(ForbiddenException):
    def __init__(self, email: str) -> None:
        super().__init__(MessageException.user_deactivated)
        self.alias = {"email": email}


class UserNotFoundException(ObjectNotFoundException):
    def __init__(self, email: str) -> None:
        super().__init__(id_=email, model_name="User")
        self.message = MessageException.user_not_found


class PasswordInvalidException(ForbiddenException):
    def __init__(self) -> None:
        super().__init__(MessageException.password_invalid)


class ForgotPasswordCodeAlreadySentException(ObjectAlreadyExistsException):
    def __init__(self, email: str) -> None:
        super().__init__(id_=email, model_name="ForgotPasswordCode")


class ForgotPasswordCodeFailedOrExpiredException(ObjectNotFoundException):
    def __init__(self, email: str) -> None:
        super().__init__(id_=email, model_name="ForgotPasswordCode")
        self.message = MessageException.forgot_password_code_failed_or_expired
