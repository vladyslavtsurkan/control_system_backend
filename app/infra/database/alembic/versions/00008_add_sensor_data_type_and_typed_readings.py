"""Add sensor data_type and typed reading value columns

Revision ID: 00008
Revises: 00007
Create Date: 2026-03-17 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "00008"
down_revision: str | None = "00007"
branch_labels: Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SENSOR_DATA_TYPE_ENUM = sa.Enum("numeric", "boolean", "string", name="sensordatatypeenum")


def upgrade() -> None:
    bind = op.get_bind()
    SENSOR_DATA_TYPE_ENUM.create(bind, checkfirst=True)

    op.add_column(
        "sensors",
        sa.Column("data_type", SENSOR_DATA_TYPE_ENUM, nullable=False, server_default="numeric"),
    )

    op.add_column("readings", sa.Column("val_num", sa.Float(), nullable=True))
    op.add_column("readings", sa.Column("val_bool", sa.Boolean(), nullable=True))
    op.add_column("readings", sa.Column("val_str", sa.Text(), nullable=True))

    op.execute(
        """
        UPDATE readings
        SET
            val_num = CASE
                WHEN jsonb_typeof(payload -> 'value') = 'number' THEN (payload ->> 'value')::double precision
                ELSE NULL
            END,
            val_bool = CASE
                WHEN jsonb_typeof(payload -> 'value') = 'boolean' THEN (payload ->> 'value')::boolean
                ELSE NULL
            END,
            val_str = CASE
                WHEN jsonb_typeof(payload -> 'value') = 'string' THEN payload ->> 'value'
                ELSE NULL
            END
        """
    )

    op.drop_index("idx_readings_payload_gin", table_name="readings")
    op.alter_column("sensors", "data_type", server_default=None)


def downgrade() -> None:
    op.create_index("idx_readings_payload_gin", "readings", ["payload"], unique=False, postgresql_using="gin")

    op.drop_column("readings", "val_str")
    op.drop_column("readings", "val_bool")
    op.drop_column("readings", "val_num")
    op.drop_column("sensors", "data_type")

    bind = op.get_bind()
    SENSOR_DATA_TYPE_ENUM.drop(bind, checkfirst=True)
