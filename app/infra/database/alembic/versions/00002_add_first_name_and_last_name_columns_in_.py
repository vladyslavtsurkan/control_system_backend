"""Add first_name and last_name columns in users table

Revision ID: 00002
Revises: 00001
Create Date: 2025-09-25 22:51:54.522024

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
    op.add_column("users", sa.Column("first_name", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(length=100), nullable=True))
    op.alter_column("users", "hashed_password", existing_type=sa.String(), nullable=False)


def downgrade() -> None:
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
    op.alter_column("users", "hashed_password", existing_type=sa.String(length=255), nullable=False)
