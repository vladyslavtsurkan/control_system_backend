"""Add audit_logs table

Revision ID: 00015
Revises: 00014
Create Date: 2026-04-12 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "00015"
down_revision: str | None = "00014"
branch_labels: Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RLS_BYPASS_VAR = "app.bypass_rls"
RLS_TENANT_VAR = "app.current_tenant_id"


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE auditactionenum AS ENUM (
                'created', 'updated', 'deleted',
                'member_added', 'member_removed', 'member_left',
                'role_changed',
                'api_key_created', 'api_key_revoked',
                'control_command_sent'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE auditresourcetypeenum AS ENUM (
                'organization', 'opc_server', 'sensor',
                'alert_rule', 'member', 'api_key'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("actor_email", sa.String(length=255), nullable=False),
        sa.Column(
            "action",
            postgresql.ENUM(
                "created",
                "updated",
                "deleted",
                "member_added",
                "member_removed",
                "member_left",
                "role_changed",
                "api_key_created",
                "api_key_revoked",
                "control_command_sent",
                name="auditactionenum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "resource_type",
            postgresql.ENUM(
                "organization",
                "opc_server",
                "sensor",
                "alert_rule",
                "member",
                "api_key",
                name="auditresourcetypeenum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("resource_id", sa.UUID(), nullable=True),
        sa.Column("resource_name", sa.String(length=255), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
            name="fk_audit_logs_organization_id",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            ondelete="SET NULL",
            name="fk_audit_logs_actor_id",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_audit_logs_organization_id", "audit_logs", ["organization_id"])
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])

    # Covering index for the common list query (newest-first per org)
    op.create_index(
        "ix_audit_logs_org_created_at",
        "audit_logs",
        ["organization_id", sa.text("created_at DESC")],
    )

    # Row-Level Security
    op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY")

    # SELECT: only rows that belong to the current tenant (or bypass is active)
    op.execute(
        """
        CREATE POLICY audit_logs_select ON audit_logs
            FOR SELECT
            USING (
                app.rls_bypass()
                OR organization_id = app.current_tenant_uuid()
            )
        """
    )

    # INSERT: allow any insert where the row's organization_id matches the
    # tenant context that was set just before the insert, or bypass is active.
    op.execute(
        """
        CREATE POLICY audit_logs_insert ON audit_logs
            FOR INSERT
            WITH CHECK (
                app.rls_bypass()
                OR organization_id = app.current_tenant_uuid()
            )
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS audit_logs_insert ON audit_logs")
    op.execute("DROP POLICY IF EXISTS audit_logs_select ON audit_logs")
    op.execute("ALTER TABLE audit_logs NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY")

    op.drop_index("ix_audit_logs_org_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_resource_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_organization_id", table_name="audit_logs")

    op.drop_table("audit_logs")

    op.execute("DROP TYPE IF EXISTS auditresourcetypeenum")
    op.execute("DROP TYPE IF EXISTS auditactionenum")
