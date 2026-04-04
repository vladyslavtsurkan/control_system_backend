"""Drop redundant indexes and trigger from readings

Revision ID: 00013
Revises: 00012
Create Date: 2026-04-04 18:40:38.553871

"""

from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "00013"
down_revision: str | None = "00012"
branch_labels: Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop redundant indexes
    op.drop_index("ix_readings_organization_id", table_name="readings")
    op.drop_index("ix_readings_sensor_id", table_name="readings")

    # Drop redundant trigger which load DB during bulk inserts
    op.execute("DROP TRIGGER IF EXISTS trg_readings_fill_organization_id ON readings")


def downgrade() -> None:
    op.execute(
        """
        CREATE TRIGGER trg_readings_fill_organization_id
        BEFORE INSERT OR UPDATE OF sensor_id ON readings
        FOR EACH ROW
        EXECUTE FUNCTION app.fill_reading_organization_id()
        """
    )

    # 2. Повертаємо індекси
    op.create_index("ix_readings_sensor_id", "readings", ["sensor_id"], unique=False)
    op.create_index("ix_readings_organization_id", "readings", ["organization_id"], unique=False)
