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

    # Auth exceptions
    verification_failed_or_expired = "verification_failed_or_expired"
    password_same_as_old = "password_same_as_old"
    could_not_validate_credentials = "could_not_validate_credentials"
    could_not_refresh_token = "could_not_refresh_token"
    user_deactivated = "user_deactivated"
    user_not_found = "user_not_found"
    password_invalid = "password_invalid"
    forgot_password_code_failed_or_expired = "forgot_password_code_failed_or_expired"

    # Tenant exceptions
    tenant_id_required = "tenant_id_required"
    invalid_tenant_id_format = "invalid_tenant_id_format"
    tenant_access_denied = "tenant_access_denied"
