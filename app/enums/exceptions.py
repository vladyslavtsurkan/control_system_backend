from app.enums.base import BaseStrEnum

__all__ = ["MessageException"]


class MessageException(BaseStrEnum):
    invalid_verification_code = "invalid_verification_code"
    object_not_found = "object_not_found"
    object_already_exists = "object_already_exists"
    gone = "gone"
    not_authorized = "not_authorized"
    forbidden = "forbidden"
    bad_request = "bad_request"
