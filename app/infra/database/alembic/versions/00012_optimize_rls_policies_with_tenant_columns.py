"""Optimize RLS policies using denormalized tenant columns

Revision ID: 00012
Revises: 00011
Create Date: 2026-04-02 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "00012"
down_revision: str | None = "00011"
branch_labels: Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "opc_servers",
    "sensors",
    "collector_api_keys",
    "readings",
    "alert_rules",
    "alerts",
    "alert_actions",
)


def _create_policy(table_name: str) -> None:
    op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table_name}")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON {table_name}
            USING (
                app.rls_bypass()
                OR organization_id = app.current_tenant_uuid()
            )
            WITH CHECK (
                app.rls_bypass()
                OR organization_id = app.current_tenant_uuid()
            )
        """
    )


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS app")

    # STABLE wrappers avoid repeated casts in each policy and keep SQL concise.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.current_tenant_uuid()
        RETURNS uuid
        LANGUAGE sql
        STABLE
        AS $$
            SELECT NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        $$
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.rls_bypass()
        RETURNS boolean
        LANGUAGE sql
        STABLE
        AS $$
            SELECT current_setting('app.bypass_rls', true) = 'true'
        $$
        """
    )

    # Add direct tenant columns to eliminate JOINs in RLS predicates.
    op.add_column("sensors", sa.Column("organization_id", sa.UUID(), nullable=True))
    op.add_column("collector_api_keys", sa.Column("organization_id", sa.UUID(), nullable=True))
    op.add_column("readings", sa.Column("organization_id", sa.UUID(), nullable=True))
    op.add_column("alert_rules", sa.Column("organization_id", sa.UUID(), nullable=True))
    op.add_column("alerts", sa.Column("organization_id", sa.UUID(), nullable=True))
    op.add_column("alert_actions", sa.Column("organization_id", sa.UUID(), nullable=True))

    op.execute(
        """
        UPDATE sensors s
        SET organization_id = os.organization_id
        FROM opc_servers os
        WHERE os.id = s.opc_server_id
          AND s.organization_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE collector_api_keys cak
        SET organization_id = os.organization_id
        FROM opc_servers os
        WHERE os.id = cak.opc_server_id
          AND cak.organization_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE readings r
        SET organization_id = s.organization_id
        FROM sensors s
        WHERE s.id = r.sensor_id
          AND r.organization_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE alert_rules ar
        SET organization_id = s.organization_id
        FROM sensors s
        WHERE s.id = ar.sensor_id
          AND ar.organization_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE alerts a
        SET organization_id = s.organization_id
        FROM sensors s
        WHERE s.id = a.sensor_id
          AND a.organization_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE alert_actions aa
        SET organization_id = ar.organization_id
        FROM alert_rules ar
        WHERE ar.id = aa.rule_id
          AND aa.organization_id IS NULL
        """
    )

    op.create_index("ix_sensors_opc_server_id", "sensors", ["opc_server_id"], unique=False)
    op.create_index("ix_readings_sensor_id", "readings", ["sensor_id"], unique=False)
    op.create_index("ix_alert_rules_sensor_id", "alert_rules", ["sensor_id"], unique=False)
    op.create_index("ix_alerts_sensor_id", "alerts", ["sensor_id"], unique=False)
    op.create_index("ix_alerts_rule_id", "alerts", ["rule_id"], unique=False)

    op.create_index("ix_sensors_organization_id", "sensors", ["organization_id"], unique=False)
    op.create_index("ix_collector_api_keys_organization_id", "collector_api_keys", ["organization_id"], unique=False)
    op.create_index("ix_readings_organization_id", "readings", ["organization_id"], unique=False)
    op.create_index("ix_alert_rules_organization_id", "alert_rules", ["organization_id"], unique=False)
    op.create_index("ix_alerts_organization_id", "alerts", ["organization_id"], unique=False)
    op.create_index("ix_alert_actions_organization_id", "alert_actions", ["organization_id"], unique=False)

    op.alter_column("sensors", "organization_id", nullable=False)
    op.alter_column("collector_api_keys", "organization_id", nullable=False)
    op.alter_column("readings", "organization_id", nullable=False)
    op.alter_column("alert_rules", "organization_id", nullable=False)
    op.alter_column("alerts", "organization_id", nullable=False)
    op.alter_column("alert_actions", "organization_id", nullable=False)

    op.create_foreign_key(
        "fk_sensors_organization_id",
        "sensors",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_collector_api_keys_organization_id",
        "collector_api_keys",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_readings_organization_id",
        "readings",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_alert_rules_organization_id",
        "alert_rules",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_alerts_organization_id",
        "alerts",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_alert_actions_organization_id",
        "alert_actions",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.fill_sensor_organization_id()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.organization_id IS NOT NULL THEN
                RETURN NEW;
            END IF;

            SELECT os.organization_id INTO NEW.organization_id
            FROM opc_servers os
            WHERE os.id = NEW.opc_server_id;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.fill_collector_api_key_organization_id()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.organization_id IS NOT NULL THEN
                RETURN NEW;
            END IF;

            SELECT os.organization_id INTO NEW.organization_id
            FROM opc_servers os
            WHERE os.id = NEW.opc_server_id;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.fill_reading_organization_id()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.organization_id IS NOT NULL THEN
                RETURN NEW;
            END IF;

            SELECT s.organization_id INTO NEW.organization_id
            FROM sensors s
            WHERE s.id = NEW.sensor_id;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.fill_alert_rule_organization_id()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.organization_id IS NOT NULL THEN
                RETURN NEW;
            END IF;

            SELECT s.organization_id INTO NEW.organization_id
            FROM sensors s
            WHERE s.id = NEW.sensor_id;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.fill_alert_organization_id()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            sensor_org uuid;
            rule_org uuid;
        BEGIN
            IF NEW.organization_id IS NOT NULL THEN
                RETURN NEW;
            END IF;

            SELECT s.organization_id INTO sensor_org
            FROM sensors s
            WHERE s.id = NEW.sensor_id;

            IF NEW.rule_id IS NOT NULL THEN
                SELECT ar.organization_id INTO rule_org
                FROM alert_rules ar
                WHERE ar.id = NEW.rule_id;

                IF rule_org IS DISTINCT FROM sensor_org THEN
                    RAISE EXCEPTION 'alert rule and sensor must belong to the same organization';
                END IF;
            END IF;

            NEW.organization_id := sensor_org;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.fill_alert_action_organization_id()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            rule_org uuid;
            target_org uuid;
        BEGIN
            IF NEW.organization_id IS NOT NULL THEN
                RETURN NEW;
            END IF;

            SELECT ar.organization_id INTO rule_org
            FROM alert_rules ar
            WHERE ar.id = NEW.rule_id;

            SELECT s.organization_id INTO target_org
            FROM sensors s
            WHERE s.id = NEW.target_sensor_id;

            IF rule_org IS DISTINCT FROM target_org THEN
                RAISE EXCEPTION 'alert action rule and target sensor must belong to the same organization';
            END IF;

            NEW.organization_id := rule_org;
            RETURN NEW;
        END;
        $$
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_sensors_fill_organization_id
        BEFORE INSERT OR UPDATE OF opc_server_id ON sensors
        FOR EACH ROW
        EXECUTE FUNCTION app.fill_sensor_organization_id()
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_collector_api_keys_fill_organization_id
        BEFORE INSERT OR UPDATE OF opc_server_id ON collector_api_keys
        FOR EACH ROW
        EXECUTE FUNCTION app.fill_collector_api_key_organization_id()
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_readings_fill_organization_id
        BEFORE INSERT OR UPDATE OF sensor_id ON readings
        FOR EACH ROW
        EXECUTE FUNCTION app.fill_reading_organization_id()
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_alert_rules_fill_organization_id
        BEFORE INSERT OR UPDATE OF sensor_id ON alert_rules
        FOR EACH ROW
        EXECUTE FUNCTION app.fill_alert_rule_organization_id()
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_alerts_fill_organization_id
        BEFORE INSERT OR UPDATE OF sensor_id, rule_id ON alerts
        FOR EACH ROW
        EXECUTE FUNCTION app.fill_alert_organization_id()
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_alert_actions_fill_organization_id
        BEFORE INSERT OR UPDATE OF rule_id, target_sensor_id ON alert_actions
        FOR EACH ROW
        EXECUTE FUNCTION app.fill_alert_action_organization_id()
        """
    )

    for table_name in TABLES:
        _create_policy(table_name)


def downgrade() -> None:
    for table_name in TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table_name}")

    op.execute("DROP TRIGGER IF EXISTS trg_alert_actions_fill_organization_id ON alert_actions")
    op.execute("DROP TRIGGER IF EXISTS trg_alerts_fill_organization_id ON alerts")
    op.execute("DROP TRIGGER IF EXISTS trg_alert_rules_fill_organization_id ON alert_rules")
    op.execute("DROP TRIGGER IF EXISTS trg_readings_fill_organization_id ON readings")
    op.execute("DROP TRIGGER IF EXISTS trg_collector_api_keys_fill_organization_id ON collector_api_keys")
    op.execute("DROP TRIGGER IF EXISTS trg_sensors_fill_organization_id ON sensors")

    op.execute("DROP FUNCTION IF EXISTS app.fill_alert_action_organization_id()")
    op.execute("DROP FUNCTION IF EXISTS app.fill_alert_organization_id()")
    op.execute("DROP FUNCTION IF EXISTS app.fill_alert_rule_organization_id()")
    op.execute("DROP FUNCTION IF EXISTS app.fill_reading_organization_id()")
    op.execute("DROP FUNCTION IF EXISTS app.fill_collector_api_key_organization_id()")
    op.execute("DROP FUNCTION IF EXISTS app.fill_sensor_organization_id()")

    op.drop_constraint("fk_alert_actions_organization_id", "alert_actions", type_="foreignkey")
    op.drop_constraint("fk_alerts_organization_id", "alerts", type_="foreignkey")
    op.drop_constraint("fk_alert_rules_organization_id", "alert_rules", type_="foreignkey")
    op.drop_constraint("fk_readings_organization_id", "readings", type_="foreignkey")
    op.drop_constraint("fk_collector_api_keys_organization_id", "collector_api_keys", type_="foreignkey")
    op.drop_constraint("fk_sensors_organization_id", "sensors", type_="foreignkey")

    op.drop_index("ix_alert_actions_organization_id", table_name="alert_actions")
    op.drop_index("ix_alerts_organization_id", table_name="alerts")
    op.drop_index("ix_alert_rules_organization_id", table_name="alert_rules")
    op.drop_index("ix_readings_organization_id", table_name="readings")
    op.drop_index("ix_collector_api_keys_organization_id", table_name="collector_api_keys")
    op.drop_index("ix_sensors_organization_id", table_name="sensors")

    op.drop_index("ix_alerts_rule_id", table_name="alerts")
    op.drop_index("ix_alerts_sensor_id", table_name="alerts")
    op.drop_index("ix_alert_rules_sensor_id", table_name="alert_rules")
    op.drop_index("ix_readings_sensor_id", table_name="readings")
    op.drop_index("ix_sensors_opc_server_id", table_name="sensors")

    op.drop_column("alert_actions", "organization_id")
    op.drop_column("alerts", "organization_id")
    op.drop_column("alert_rules", "organization_id")
    op.drop_column("readings", "organization_id")
    op.drop_column("collector_api_keys", "organization_id")
    op.drop_column("sensors", "organization_id")

    op.execute("DROP FUNCTION IF EXISTS app.rls_bypass()")
    op.execute("DROP FUNCTION IF EXISTS app.current_tenant_uuid()")

    op.execute(
        """
        CREATE POLICY tenant_isolation ON opc_servers
            USING (
                current_setting('app.bypass_rls', true) = 'true'
                OR (
                    current_setting('app.current_tenant_id', true) != ''
                    AND organization_id = current_setting('app.current_tenant_id', true)::uuid
                )
            )
        """
    )
    op.execute(
        """
        CREATE POLICY tenant_isolation ON sensors
            USING (
                current_setting('app.bypass_rls', true) = 'true'
                OR (
                    current_setting('app.current_tenant_id', true) != ''
                    AND EXISTS (
                        SELECT 1 FROM opc_servers
                        WHERE opc_servers.id = sensors.opc_server_id
                          AND opc_servers.organization_id = current_setting('app.current_tenant_id', true)::uuid
                    )
                )
            )
        """
    )
    op.execute(
        """
        CREATE POLICY tenant_isolation ON collector_api_keys
            USING (
                current_setting('app.bypass_rls', true) = 'true'
                OR (
                    current_setting('app.current_tenant_id', true) != ''
                    AND EXISTS (
                        SELECT 1 FROM opc_servers
                        WHERE opc_servers.id = collector_api_keys.opc_server_id
                          AND opc_servers.organization_id = current_setting('app.current_tenant_id', true)::uuid
                    )
                )
            )
        """
    )
    op.execute(
        """
        CREATE POLICY tenant_isolation ON readings
            USING (
                current_setting('app.bypass_rls', true) = 'true'
                OR (
                    current_setting('app.current_tenant_id', true) != ''
                    AND EXISTS (
                        SELECT 1 FROM sensors
                        JOIN opc_servers ON opc_servers.id = sensors.opc_server_id
                        WHERE sensors.id = readings.sensor_id
                          AND opc_servers.organization_id = current_setting('app.current_tenant_id', true)::uuid
                    )
                )
            )
        """
    )
    op.execute(
        """
        CREATE POLICY tenant_isolation ON alert_rules
            USING (
                current_setting('app.bypass_rls', true) = 'true'
                OR (
                    current_setting('app.current_tenant_id', true) != ''
                    AND EXISTS (
                        SELECT 1 FROM sensors
                        JOIN opc_servers ON opc_servers.id = sensors.opc_server_id
                        WHERE sensors.id = alert_rules.sensor_id
                          AND opc_servers.organization_id = current_setting('app.current_tenant_id', true)::uuid
                    )
                )
            )
        """
    )
    op.execute(
        """
        CREATE POLICY tenant_isolation ON alerts
            USING (
                current_setting('app.bypass_rls', true) = 'true'
                OR (
                    current_setting('app.current_tenant_id', true) != ''
                    AND EXISTS (
                        SELECT 1 FROM sensors
                        JOIN opc_servers ON opc_servers.id = sensors.opc_server_id
                        WHERE sensors.id = alerts.sensor_id
                          AND opc_servers.organization_id = current_setting('app.current_tenant_id', true)::uuid
                    )
                )
            )
        """
    )
    op.execute(
        """
        CREATE POLICY tenant_isolation ON alert_actions
            USING (
                current_setting('app.bypass_rls', true) = 'true'
                OR (
                    current_setting('app.current_tenant_id', true) != ''
                    AND EXISTS (
                        SELECT 1 FROM sensors
                        JOIN opc_servers ON opc_servers.id = sensors.opc_server_id
                        WHERE sensors.id = alert_actions.target_sensor_id
                          AND opc_servers.organization_id = current_setting('app.current_tenant_id', true)::uuid
                    )
                )
            )
        """
    )
