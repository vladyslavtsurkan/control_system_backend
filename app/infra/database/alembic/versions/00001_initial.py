"""Initial

Revision ID: 00001
Revises:
Create Date: 2026-03-06 23:22:08.002189

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "00001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        "idx_organizations_active", "organizations", ["id"], unique=False, postgresql_where=sa.text("NOT is_deleted")
    )
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "opc_servers",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("url", sa.String(length=512), nullable=False),
        sa.Column(
            "security_policy",
            sa.Enum(
                "AES256_SHA256_RSAPSS",
                "AES128_SHA256_RSAOAEP",
                "BASIC256_SHA256",
                "NONE",
                "BASIC256",
                "BASIC128_RSA15",
                name="securitypolicyenum",
            ),
            nullable=False,
        ),
        sa.Column("authentication_method", sa.Enum("ANONYMOUS", "USERNAME", name="authmethodenum"), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("encrypted_password", sa.String(length=255), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_opc_servers_organization_id"), "opc_servers", ["organization_id"], unique=False)
    op.create_index(
        "uq_active_opc_server_name",
        "opc_servers",
        ["organization_id", "name"],
        unique=True,
        postgresql_where=sa.text("NOT is_deleted"),
    )
    op.create_table(
        "user_organization_association",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.Enum("OWNER", "ADMIN", "MEMBER", name="userroleinorgenum"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "organization_id"),
    )
    op.create_index(
        "idx_org_users_reverse", "user_organization_association", ["organization_id", "user_id"], unique=False
    )
    op.create_table(
        "sensors",
        sa.Column("opc_server_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("node_id", sa.String(length=255), nullable=False),
        sa.Column("units", sa.String(length=50), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["opc_server_id"], ["opc_servers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_active_sensor_node",
        "sensors",
        ["opc_server_id", "node_id"],
        unique=False,
        postgresql_where=sa.text("NOT is_deleted"),
    )
    op.create_index(
        "uq_active_sensor_name",
        "sensors",
        ["opc_server_id", "name"],
        unique=True,
        postgresql_where=sa.text("NOT is_deleted"),
    )
    op.create_table(
        "alert_rules",
        sa.Column("sensor_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "severity", sa.Enum("INFO", "WARNING", "CRITICAL", "FATAL", name="alertseverityenum"), nullable=False
        ),
        sa.Column(
            "condition",
            sa.Enum(
                "GREATER_THAN",
                "LESS_THAN",
                "EQUALS",
                "NOT_EQUALS",
                "OUTSIDE_RANGE",
                "INSIDE_RANGE",
                "NO_DATA",
                name="alertconditionenum",
            ),
            nullable=False,
        ),
        sa.Column("threshold", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sensor_id"], ["sensors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_active_alert_rules",
        "alert_rules",
        ["sensor_id"],
        unique=False,
        postgresql_where=sa.text("is_active IS TRUE"),
    )
    op.create_table(
        "readings",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sensor_id", sa.UUID(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["sensor_id"], ["sensors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("time", "sensor_id"),
        timescaledb_hypertable={"time_column_name": "time", "chunk_time_interval": "1 day"},
    )
    op.create_index("idx_readings_payload_gin", "readings", ["payload"], unique=False, postgresql_using="gin")
    op.create_index("idx_readings_sensor_time_desc", "readings", ["sensor_id", "time"], unique=False)
    op.create_table(
        "alerts",
        sa.Column("sensor_id", sa.UUID(), nullable=False),
        sa.Column("rule_id", sa.UUID(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("triggered_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_acknowledged", sa.Boolean(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["alert_rules.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sensor_id"], ["sensors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_active_alerts", "alerts", ["sensor_id"], unique=False, postgresql_where=sa.text("resolved_at IS NULL")
    )
    op.create_index("idx_alerts_sensor_id_desc", "alerts", ["sensor_id", "id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_alerts_sensor_id_desc", table_name="alerts")
    op.drop_index("idx_active_alerts", table_name="alerts", postgresql_where=sa.text("resolved_at IS NULL"))
    op.drop_table("alerts")
    op.drop_index("idx_readings_sensor_time_desc", table_name="readings")
    op.drop_index("idx_readings_payload_gin", table_name="readings", postgresql_using="gin")
    op.drop_table("readings")
    op.drop_index("idx_active_alert_rules", table_name="alert_rules", postgresql_where=sa.text("is_active IS TRUE"))
    op.drop_table("alert_rules")
    op.drop_index("uq_active_sensor_name", table_name="sensors", postgresql_where=sa.text("NOT is_deleted"))
    op.drop_index("idx_active_sensor_node", table_name="sensors", postgresql_where=sa.text("NOT is_deleted"))
    op.drop_table("sensors")
    op.drop_index("idx_org_users_reverse", table_name="user_organization_association")
    op.drop_table("user_organization_association")
    op.drop_index("uq_active_opc_server_name", table_name="opc_servers", postgresql_where=sa.text("NOT is_deleted"))
    op.drop_index(op.f("ix_opc_servers_organization_id"), table_name="opc_servers")
    op.drop_table("opc_servers")
    op.drop_table("users")
    op.drop_index("idx_organizations_active", table_name="organizations", postgresql_where=sa.text("NOT is_deleted"))
    op.drop_table("organizations")
