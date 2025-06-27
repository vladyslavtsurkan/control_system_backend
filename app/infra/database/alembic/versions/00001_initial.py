"""Initial

Revision ID: 00001
Revises:
Create Date: 2025-06-27 22:35:27.754192

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "00001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_organizations_created_at"), "organizations", ["created_at"], unique=False)
    op.create_index(op.f("ix_organizations_id"), "organizations", ["id"], unique=False)
    op.create_index(op.f("ix_organizations_is_deleted"), "organizations", ["is_deleted"], unique=False)
    op.create_index(op.f("ix_organizations_name"), "organizations", ["name"], unique=True)
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_created_at"), "users", ["created_at"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_table(
        "opc_servers",
        sa.Column("organization_id", sa.UUID(), nullable=False),
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
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "name", name="uq_opc_server_organization_name"),
    )
    op.create_index(op.f("ix_opc_servers_created_at"), "opc_servers", ["created_at"], unique=False)
    op.create_index(op.f("ix_opc_servers_id"), "opc_servers", ["id"], unique=False)
    op.create_index(op.f("ix_opc_servers_is_deleted"), "opc_servers", ["is_deleted"], unique=False)
    op.create_index(op.f("ix_opc_servers_name"), "opc_servers", ["name"], unique=True)
    op.create_table(
        "user_organization_association",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.Enum("OWNER", "ADMIN", "MEMBER", name="userroleinorgenum"), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_user_organization_association"),
    )
    op.create_index(op.f("ix_user_organization_association_id"), "user_organization_association", ["id"], unique=False)
    op.create_table(
        "sensors",
        sa.Column("opc_server_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("node_id", sa.String(length=255), nullable=False),
        sa.Column("units", sa.String(length=50), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["opc_server_id"], ["opc_servers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("opc_server_id", "name", name="uq_sensor_opc_server_name"),
    )
    op.create_index(op.f("ix_sensors_created_at"), "sensors", ["created_at"], unique=False)
    op.create_index(op.f("ix_sensors_id"), "sensors", ["id"], unique=False)
    op.create_index(op.f("ix_sensors_is_deleted"), "sensors", ["is_deleted"], unique=False)
    op.create_table(
        "alerts",
        sa.Column("sensor_id", sa.UUID(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("triggered_value", sa.Float(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sensor_id"], ["sensors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alerts_created_at"), "alerts", ["created_at"], unique=False)
    op.create_index(op.f("ix_alerts_id"), "alerts", ["id"], unique=False)
    op.create_table(
        "readings",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sensor_id", sa.UUID(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["sensor_id"], ["sensors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("time", "sensor_id"),
        timescaledb_hypertable={"time_column_name": "time", "chunk_time_interval": "1 day"},
    )


def downgrade() -> None:
    op.drop_table("readings")
    op.drop_index(op.f("ix_alerts_id"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_created_at"), table_name="alerts")
    op.drop_table("alerts")
    op.drop_index(op.f("ix_sensors_is_deleted"), table_name="sensors")
    op.drop_index(op.f("ix_sensors_id"), table_name="sensors")
    op.drop_index(op.f("ix_sensors_created_at"), table_name="sensors")
    op.drop_table("sensors")
    op.drop_index(op.f("ix_user_organization_association_id"), table_name="user_organization_association")
    op.drop_table("user_organization_association")
    op.drop_index(op.f("ix_opc_servers_name"), table_name="opc_servers")
    op.drop_index(op.f("ix_opc_servers_is_deleted"), table_name="opc_servers")
    op.drop_index(op.f("ix_opc_servers_id"), table_name="opc_servers")
    op.drop_index(op.f("ix_opc_servers_created_at"), table_name="opc_servers")
    op.drop_table("opc_servers")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_created_at"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_organizations_name"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_is_deleted"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_id"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_created_at"), table_name="organizations")
    op.drop_table("organizations")
