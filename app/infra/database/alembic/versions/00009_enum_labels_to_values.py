"""Rename enum labels to stored value strings

Revision ID: 00009
Revises: 00008
Create Date: 2026-03-17 13:20:00.000000

"""

from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "00009"
down_revision: str | None = "00008"
branch_labels: Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _rename_enum_value(enum_name: str, old_value: str, new_value: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = '{enum_name}'
                  AND e.enumlabel = '{old_value}'
            ) THEN
                ALTER TYPE {enum_name} RENAME VALUE '{old_value}' TO '{new_value}';
            END IF;
        END
        $$;
        """
    )


def upgrade() -> None:
    # alertseverityenum
    _rename_enum_value("alertseverityenum", "INFO", "info")
    _rename_enum_value("alertseverityenum", "WARNING", "warning")
    _rename_enum_value("alertseverityenum", "CRITICAL", "critical")
    _rename_enum_value("alertseverityenum", "FATAL", "fatal")

    # alertconditionenum
    _rename_enum_value("alertconditionenum", "GREATER_THAN", "greater_than")
    _rename_enum_value("alertconditionenum", "LESS_THAN", "less_than")
    _rename_enum_value("alertconditionenum", "EQUALS", "equals")
    _rename_enum_value("alertconditionenum", "NOT_EQUALS", "not_equals")
    _rename_enum_value("alertconditionenum", "OUTSIDE_RANGE", "outside_range")
    _rename_enum_value("alertconditionenum", "INSIDE_RANGE", "inside_range")
    _rename_enum_value("alertconditionenum", "NO_DATA", "no_data")

    # authmethodenum
    _rename_enum_value("authmethodenum", "ANONYMOUS", "anonymous")
    _rename_enum_value("authmethodenum", "USERNAME", "username")

    # userroleinorgenum
    _rename_enum_value("userroleinorgenum", "OWNER", "owner")
    _rename_enum_value("userroleinorgenum", "ADMIN", "admin")
    _rename_enum_value("userroleinorgenum", "MEMBER", "member")

    # securitypolicyenum
    _rename_enum_value("securitypolicyenum", "AES256_SHA256_RSAPSS", "Aes256_Sha256_RsaPss")
    _rename_enum_value("securitypolicyenum", "AES128_SHA256_RSAOAEP", "Aes128_Sha256_RsaOaep")
    _rename_enum_value("securitypolicyenum", "BASIC256_SHA256", "Basic256Sha256")
    _rename_enum_value("securitypolicyenum", "NONE", "None")
    _rename_enum_value("securitypolicyenum", "BASIC256", "Basic256")
    _rename_enum_value("securitypolicyenum", "BASIC128_RSA15", "Basic128Rsa15")


def downgrade() -> None:
    # securitypolicyenum
    _rename_enum_value("securitypolicyenum", "Aes256_Sha256_RsaPss", "AES256_SHA256_RSAPSS")
    _rename_enum_value("securitypolicyenum", "Aes128_Sha256_RsaOaep", "AES128_SHA256_RSAOAEP")
    _rename_enum_value("securitypolicyenum", "Basic256Sha256", "BASIC256_SHA256")
    _rename_enum_value("securitypolicyenum", "None", "NONE")
    _rename_enum_value("securitypolicyenum", "Basic256", "BASIC256")
    _rename_enum_value("securitypolicyenum", "Basic128Rsa15", "BASIC128_RSA15")

    # userroleinorgenum
    _rename_enum_value("userroleinorgenum", "owner", "OWNER")
    _rename_enum_value("userroleinorgenum", "admin", "ADMIN")
    _rename_enum_value("userroleinorgenum", "member", "MEMBER")

    # authmethodenum
    _rename_enum_value("authmethodenum", "anonymous", "ANONYMOUS")
    _rename_enum_value("authmethodenum", "username", "USERNAME")

    # alertconditionenum
    _rename_enum_value("alertconditionenum", "greater_than", "GREATER_THAN")
    _rename_enum_value("alertconditionenum", "less_than", "LESS_THAN")
    _rename_enum_value("alertconditionenum", "equals", "EQUALS")
    _rename_enum_value("alertconditionenum", "not_equals", "NOT_EQUALS")
    _rename_enum_value("alertconditionenum", "outside_range", "OUTSIDE_RANGE")
    _rename_enum_value("alertconditionenum", "inside_range", "INSIDE_RANGE")
    _rename_enum_value("alertconditionenum", "no_data", "NO_DATA")

    # alertseverityenum
    _rename_enum_value("alertseverityenum", "info", "INFO")
    _rename_enum_value("alertseverityenum", "warning", "WARNING")
    _rename_enum_value("alertseverityenum", "critical", "CRITICAL")
    _rename_enum_value("alertseverityenum", "fatal", "FATAL")
