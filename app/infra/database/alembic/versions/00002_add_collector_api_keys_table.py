"""Add collector_api_keys table

Revision ID: 00002
Revises: 00001
Create Date: 2026-03-07 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "00002"
down_revision: str | None = "00001"
branch_labels: Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "collector_api_keys",
        sa.Column("opc_server_id", sa.UUID(), nullable=False),
        sa.Column("key_prefix", sa.String(length=20), nullable=False),
        sa.Column("hashed_key", sa.String(length=255), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["opc_server_id"], ["opc_servers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("opc_server_id"),
    )


def downgrade() -> None:
    op.drop_table("collector_api_keys")
