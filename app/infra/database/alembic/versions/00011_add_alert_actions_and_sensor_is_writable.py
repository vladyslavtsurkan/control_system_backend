"""Add alert_actions table and sensor is_writable flag

Revision ID: 00011
Revises: 00010
Create Date: 2026-04-01 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "00011"
down_revision: str | None = "00010"
branch_labels: Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RLS_TENANT_VAR = "app.current_tenant_id"
RLS_BYPASS_VAR = "app.bypass_rls"


def upgrade() -> None:
    op.add_column(
        "sensors",
        sa.Column("is_writable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.alter_column("sensors", "is_writable", server_default=None)

    op.create_table(
        "alert_actions",
        sa.Column("rule_id", sa.UUID(), nullable=False),
        sa.Column("target_sensor_id", sa.UUID(), nullable=False),
        sa.Column("trigger_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("resolve_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["alert_rules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_sensor_id"], ["sensors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alert_actions_rule_id"), "alert_actions", ["rule_id"], unique=False)
    op.create_index(op.f("ix_alert_actions_target_sensor_id"), "alert_actions", ["target_sensor_id"], unique=False)

    op.execute("ALTER TABLE alert_actions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE alert_actions FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON alert_actions
            USING (
                current_setting('{RLS_BYPASS_VAR}', true) = 'true'
                OR (
                    current_setting('{RLS_TENANT_VAR}', true) != ''
                    AND EXISTS (
                        SELECT 1 FROM sensors
                        JOIN opc_servers ON opc_servers.id = sensors.opc_server_id
                        WHERE sensors.id = alert_actions.target_sensor_id
                          AND opc_servers.organization_id = current_setting('{RLS_TENANT_VAR}', true)::uuid
                    )
                )
            )
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON alert_actions")
    op.execute("ALTER TABLE alert_actions NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE alert_actions DISABLE ROW LEVEL SECURITY")

    op.drop_index(op.f("ix_alert_actions_target_sensor_id"), table_name="alert_actions")
    op.drop_index(op.f("ix_alert_actions_rule_id"), table_name="alert_actions")
    op.drop_table("alert_actions")
    op.drop_column("sensors", "is_writable")
