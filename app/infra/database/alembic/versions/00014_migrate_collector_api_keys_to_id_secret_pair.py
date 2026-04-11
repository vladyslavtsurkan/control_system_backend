"""Migrate collector_api_keys to key_id + secret pair, allow multiple keys per OPC server

Revision ID: 00014
Revises: 00013
Create Date: 2026-04-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "00014"
down_revision: str | None = "00013"
branch_labels: Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop the index on key_prefix before dropping the column
    op.drop_index("ix_collector_api_keys_key_prefix", table_name="collector_api_keys")

    # Drop key_prefix column
    op.drop_column("collector_api_keys", "key_prefix")

    # Drop unique constraint on opc_server_id (enables multiple keys per server)
    op.drop_constraint("collector_api_keys_opc_server_id_key", "collector_api_keys", type_="unique")

    # Add a plain index on opc_server_id for efficient multi-key lookups
    op.create_index("ix_collector_api_keys_opc_server_id", "collector_api_keys", ["opc_server_id"], unique=False)

    # Add key_id as nullable first so existing rows don't conflict
    op.add_column(
        "collector_api_keys",
        sa.Column("key_id", sa.String(length=64), nullable=True),
    )

    # Back-fill existing rows with unique hex values.
    op.execute("UPDATE collector_api_keys SET key_id = md5(random()::text || id::text)")

    # Now that every row has a unique value, tighten to NOT NULL
    op.alter_column("collector_api_keys", "key_id", nullable=False)

    # Add unique index on key_id
    op.create_index("ix_collector_api_keys_key_id", "collector_api_keys", ["key_id"], unique=True)


def downgrade() -> None:
    # Drop key_id index and column
    op.drop_index("ix_collector_api_keys_key_id", table_name="collector_api_keys")
    op.drop_column("collector_api_keys", "key_id")

    # Restore unique constraint on opc_server_id
    op.drop_index("ix_collector_api_keys_opc_server_id", table_name="collector_api_keys")
    op.create_unique_constraint("collector_api_keys_opc_server_id_key", "collector_api_keys", ["opc_server_id"])

    # Re-add key_prefix column (data is lost; populate with placeholder)
    op.add_column(
        "collector_api_keys",
        sa.Column("key_prefix", sa.String(length=20), nullable=False, server_default="sk_live_????????..."),
    )
    op.create_index("ix_collector_api_keys_key_prefix", "collector_api_keys", ["key_prefix"], unique=False)
    op.alter_column("collector_api_keys", "key_prefix", server_default=None)
