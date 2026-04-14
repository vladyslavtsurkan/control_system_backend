"""Migrate is_deleted (bool) to deleted_at (timestamptz) on organizations, opc_servers, sensors

Revision ID: 00016
Revises: 00015
Create Date: 2026-04-14 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "00016"
down_revision: str | None = "00015"
branch_labels: Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # organizations
    # Drop the old partial index that uses the boolean column
    op.drop_index("idx_organizations_active", table_name="organizations")

    # Add the new nullable timestamp column
    op.add_column("organizations", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    # Back-fill: rows that were logically deleted get a timestamp
    op.execute("UPDATE organizations SET deleted_at = NOW() WHERE is_deleted = TRUE")

    # Drop the old boolean column
    op.drop_column("organizations", "is_deleted")

    # Recreate the partial index using the new column
    op.create_index(
        "idx_organizations_active",
        "organizations",
        ["id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # opc_servers
    op.drop_index("uq_active_opc_server_name", table_name="opc_servers")

    op.add_column("opc_servers", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE opc_servers SET deleted_at = NOW() WHERE is_deleted = TRUE")

    op.drop_column("opc_servers", "is_deleted")

    op.create_index(
        "uq_active_opc_server_name",
        "opc_servers",
        ["organization_id", "name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # sensors
    op.drop_index("uq_active_sensor_name", table_name="sensors")
    op.drop_index("idx_active_sensor_node", table_name="sensors")

    op.add_column("sensors", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE sensors SET deleted_at = NOW() WHERE is_deleted = TRUE")

    op.drop_column("sensors", "is_deleted")

    op.create_index(
        "uq_active_sensor_name",
        "sensors",
        ["opc_server_id", "name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "idx_active_sensor_node",
        "sensors",
        ["opc_server_id", "node_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    # sensors
    op.drop_index("idx_active_sensor_node", table_name="sensors")
    op.drop_index("uq_active_sensor_name", table_name="sensors")

    op.add_column("sensors", sa.Column("is_deleted", sa.Boolean(), nullable=True))

    op.execute("UPDATE sensors SET is_deleted = (deleted_at IS NOT NULL)")
    op.execute("ALTER TABLE sensors ALTER COLUMN is_deleted SET NOT NULL")
    op.execute("ALTER TABLE sensors ALTER COLUMN is_deleted SET DEFAULT FALSE")

    op.drop_column("sensors", "deleted_at")

    op.create_index(
        "uq_active_sensor_name",
        "sensors",
        ["opc_server_id", "name"],
        unique=True,
        postgresql_where=sa.text("NOT is_deleted"),
    )
    op.create_index(
        "idx_active_sensor_node",
        "sensors",
        ["opc_server_id", "node_id"],
        postgresql_where=sa.text("NOT is_deleted"),
    )

    # opc_servers
    op.drop_index("uq_active_opc_server_name", table_name="opc_servers")

    op.add_column("opc_servers", sa.Column("is_deleted", sa.Boolean(), nullable=True))

    op.execute("UPDATE opc_servers SET is_deleted = (deleted_at IS NOT NULL)")
    op.execute("ALTER TABLE opc_servers ALTER COLUMN is_deleted SET NOT NULL")
    op.execute("ALTER TABLE opc_servers ALTER COLUMN is_deleted SET DEFAULT FALSE")

    op.drop_column("opc_servers", "deleted_at")

    op.create_index(
        "uq_active_opc_server_name",
        "opc_servers",
        ["organization_id", "name"],
        unique=True,
        postgresql_where=sa.text("NOT is_deleted"),
    )

    # organizations
    op.drop_index("idx_organizations_active", table_name="organizations")

    op.add_column("organizations", sa.Column("is_deleted", sa.Boolean(), nullable=True))

    op.execute("UPDATE organizations SET is_deleted = (deleted_at IS NOT NULL)")
    op.execute("ALTER TABLE organizations ALTER COLUMN is_deleted SET NOT NULL")
    op.execute("ALTER TABLE organizations ALTER COLUMN is_deleted SET DEFAULT FALSE")

    op.drop_column("organizations", "deleted_at")

    op.create_index(
        "idx_organizations_active",
        "organizations",
        ["id"],
        unique=False,
        postgresql_where=sa.text("NOT is_deleted"),
    )
