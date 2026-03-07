"""Add index (key_prefix) on collector_api_keys table

Revision ID: 00004
Revises: 00003
Create Date: 2026-03-07 14:34:41.807012

"""

from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "00004"
down_revision: str | None = "00003"
branch_labels: Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(op.f("ix_collector_api_keys_key_prefix"), "collector_api_keys", ["key_prefix"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_collector_api_keys_key_prefix"), table_name="collector_api_keys")
