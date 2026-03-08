"""Add RLS policies for tenant isolation

Revision ID: 00005
Revises: 00004
Create Date: 2026-03-07 15:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "00005"
down_revision: str | None = "00004"
branch_labels: Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RLS_TENANT_VAR = "app.current_tenant_id"
RLS_BYPASS_VAR = "app.bypass_rls"


def upgrade() -> None:
    # ── opc_servers (direct: has organization_id) ────────────────────────
    op.execute("ALTER TABLE opc_servers ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE opc_servers FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON opc_servers
            USING (
                current_setting('{RLS_BYPASS_VAR}', true) = 'true'
                OR (
                    current_setting('{RLS_TENANT_VAR}', true) != ''
                    AND organization_id = current_setting('{RLS_TENANT_VAR}', true)::uuid
                )
            )
        """
    )

    # ── sensors (indirect via opc_servers.opc_server_id → organization_id)
    op.execute("ALTER TABLE sensors ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sensors FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON sensors
            USING (
                current_setting('{RLS_BYPASS_VAR}', true) = 'true'
                OR (
                    current_setting('{RLS_TENANT_VAR}', true) != ''
                    AND EXISTS (
                        SELECT 1 FROM opc_servers
                        WHERE opc_servers.id = sensors.opc_server_id
                          AND opc_servers.organization_id = current_setting('{RLS_TENANT_VAR}', true)::uuid
                    )
                )
            )
        """
    )

    # ── collector_api_keys (indirect via opc_servers) ────────────────────
    op.execute("ALTER TABLE collector_api_keys ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE collector_api_keys FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON collector_api_keys
            USING (
                current_setting('{RLS_BYPASS_VAR}', true) = 'true'
                OR (
                    current_setting('{RLS_TENANT_VAR}', true) != ''
                    AND EXISTS (
                        SELECT 1 FROM opc_servers
                        WHERE opc_servers.id = collector_api_keys.opc_server_id
                          AND opc_servers.organization_id = current_setting('{RLS_TENANT_VAR}', true)::uuid
                    )
                )
            )
        """
    )

    # ── readings (indirect via sensors → opc_servers) ────────────────────
    op.execute("ALTER TABLE readings ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE readings FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON readings
            USING (
                current_setting('{RLS_BYPASS_VAR}', true) = 'true'
                OR (
                    current_setting('{RLS_TENANT_VAR}', true) != ''
                    AND EXISTS (
                        SELECT 1 FROM sensors
                        JOIN opc_servers ON opc_servers.id = sensors.opc_server_id
                        WHERE sensors.id = readings.sensor_id
                          AND opc_servers.organization_id = current_setting('{RLS_TENANT_VAR}', true)::uuid
                    )
                )
            )
        """
    )

    # ── alert_rules (indirect via sensors → opc_servers) ─────────────────
    op.execute("ALTER TABLE alert_rules ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE alert_rules FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON alert_rules
            USING (
                current_setting('{RLS_BYPASS_VAR}', true) = 'true'
                OR (
                    current_setting('{RLS_TENANT_VAR}', true) != ''
                    AND EXISTS (
                        SELECT 1 FROM sensors
                        JOIN opc_servers ON opc_servers.id = sensors.opc_server_id
                        WHERE sensors.id = alert_rules.sensor_id
                          AND opc_servers.organization_id = current_setting('{RLS_TENANT_VAR}', true)::uuid
                    )
                )
            )
        """
    )

    # ── alerts (indirect via sensors → opc_servers) ──────────────────────
    op.execute("ALTER TABLE alerts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE alerts FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON alerts
            USING (
                current_setting('{RLS_BYPASS_VAR}', true) = 'true'
                OR (
                    current_setting('{RLS_TENANT_VAR}', true) != ''
                    AND EXISTS (
                        SELECT 1 FROM sensors
                        JOIN opc_servers ON opc_servers.id = sensors.opc_server_id
                        WHERE sensors.id = alerts.sensor_id
                          AND opc_servers.organization_id = current_setting('{RLS_TENANT_VAR}', true)::uuid
                    )
                )
            )
        """
    )


def downgrade() -> None:
    for table in ("alerts", "alert_rules", "readings", "collector_api_keys", "sensors", "opc_servers"):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
