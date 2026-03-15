"""Enforce single active alert per sensor/rule

Revision ID: 00007
Revises: 00006
Create Date: 2026-03-14 13:30:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "00007"
down_revision: str | None = "00006"
branch_labels: Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Keep the newest active alert and resolve older duplicates per (sensor_id, rule_id).
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY sensor_id, rule_id
                    ORDER BY created_at DESC, id DESC
                ) AS rn
            FROM alerts
            WHERE resolved_at IS NULL
              AND rule_id IS NOT NULL
        )
        UPDATE alerts a
        SET resolved_at = NOW()
        FROM ranked r
        WHERE a.id = r.id
          AND r.rn > 1
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_active_alert_per_rule
        ON alerts (sensor_id, rule_id)
        WHERE resolved_at IS NULL
          AND rule_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_active_alert_per_rule")
