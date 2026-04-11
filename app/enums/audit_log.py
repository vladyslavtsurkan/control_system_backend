from app.enums.base import BaseStrEnum

__all__ = ["AuditActionEnum", "AuditResourceTypeEnum"]


class AuditActionEnum(BaseStrEnum):
    created = "created"
    updated = "updated"
    deleted = "deleted"
    member_added = "member_added"
    member_removed = "member_removed"
    member_left = "member_left"
    role_changed = "role_changed"
    api_key_created = "api_key_created"
    api_key_revoked = "api_key_revoked"
    control_command_sent = "control_command_sent"


class AuditResourceTypeEnum(BaseStrEnum):
    organization = "organization"
    opc_server = "opc_server"
    sensor = "sensor"
    alert_rule = "alert_rule"
    member = "member"
    api_key = "api_key"
