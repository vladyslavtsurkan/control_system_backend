"""Change OPC server encrypted_password length

Revision ID: 00003
Revises: 00002
Create Date: 2026-03-07 13:20:11.510162

"""

from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "00003"
down_revision: str | None = "00002"
branch_labels: Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE opc_servers ALTER COLUMN encrypted_password TYPE VARCHAR(512)")


def downgrade() -> None:
    op.execute("ALTER TABLE opc_servers ALTER COLUMN encrypted_password TYPE VARCHAR(255)")
