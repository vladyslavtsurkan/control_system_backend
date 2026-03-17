from app.enums.base import BaseStrEnum

__all__ = ["MessageException"]


class MessageException(BaseStrEnum):
    INVALID_VERIFICATION_CODE = "invalid_verification_code"
    OBJECT_NOT_FOUND = "object_not_found"
    OBJECT_ALREADY_EXISTS = "object_already_exists"
    GONE = "gone"
    NOT_AUTHORIZED = "not_authorized"
    FORBIDDEN = "forbidden"
    BAD_REQUEST = "bad_request"

    # Auth exceptions
    VERIFICATION_FAILED_OR_EXPIRED = "verification_failed_or_expired"
    PASSWORD_SAME_AS_OLD = "password_same_as_old"
    COULD_NOT_VALIDATE_CREDENTIALS = "could_not_validate_credentials"
    COULD_NOT_REFRESH_TOKEN = "could_not_refresh_token"
    USER_DEACTIVATED = "user_deactivated"
    USER_NOT_FOUND = "user_not_found"
    PASSWORD_INVALID = "password_invalid"
    FORGOT_PASSWORD_CODE_FAILED_OR_EXPIRED = "forgot_password_code_failed_or_expired"

    # Organization exceptions
    ORGANIZATION_ACCESS_DENIED = "organization_access_denied"
    ORGANIZATION_PERMISSION_DENIED = "organization_permission_denied"
    CANNOT_REMOVE_OWNER = "cannot_remove_owner"
    ADMIN_CAN_ONLY_REMOVE_MEMBERS = "admin_can_only_remove_members"
    OWNER_CANNOT_LEAVE = "owner_cannot_leave"
    CANNOT_CHANGE_OWN_ROLE = "cannot_change_own_role"
    ROLE_ALREADY_ASSIGNED = "role_already_assigned"

    # Tenant exceptions
    TENANT_ID_REQUIRED = "tenant_id_required"
    INVALID_TENANT_ID_FORMAT = "invalid_tenant_id_format"
    TENANT_ACCESS_DENIED = "tenant_access_denied"
