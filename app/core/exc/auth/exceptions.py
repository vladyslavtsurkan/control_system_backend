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
        self.message = MessageException.VERIFICATION_FAILED_OR_EXPIRED


class InvalidCredentialsException(NotAuthorizedException):
    def __init__(self) -> None:
        super().__init__(MessageException.COULD_NOT_VALIDATE_CREDENTIALS)


class TokenRefreshException(ForbiddenException):
    def __init__(self) -> None:
        super().__init__(MessageException.COULD_NOT_REFRESH_TOKEN)


class UserDeactivatedException(ForbiddenException):
    def __init__(self, email: str) -> None:
        super().__init__(MessageException.USER_DEACTIVATED)
        self.alias = {"email": email}


class UserNotFoundException(ObjectNotFoundException):
    def __init__(self, email: str) -> None:
        super().__init__(id_=email, model_name="User")
        self.message = MessageException.USER_NOT_FOUND


class PasswordInvalidException(ForbiddenException):
    def __init__(self) -> None:
        super().__init__(MessageException.PASSWORD_INVALID)


class ForgotPasswordCodeAlreadySentException(ObjectAlreadyExistsException):
    def __init__(self, email: str) -> None:
        super().__init__(id_=email, model_name="ForgotPasswordCode")


class ForgotPasswordCodeFailedOrExpiredException(ObjectNotFoundException):
    def __init__(self, email: str) -> None:
        super().__init__(id_=email, model_name="ForgotPasswordCode")
        self.message = MessageException.FORGOT_PASSWORD_CODE_FAILED_OR_EXPIRED
