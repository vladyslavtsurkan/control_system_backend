"""Enable Row-Level Security for multi-tenancy

Revision ID: 00003
Revises: 00002
Create Date: 2026-01-30

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "00003"
down_revision: str | None = "00002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tables that require RLS policies (tenant-aware tables)
RLS_TABLES = [
    "opc_servers",
    "sensors",
    "readings",
    "alerts",
]

# Tables with indirect tenant relationship (through opc_servers -> sensors)
INDIRECT_RLS_TABLES = {
    "sensors": ("opc_server_id", "opc_servers", "id"),
    "readings": ("sensor_id", "sensors", "id"),
    "alerts": ("sensor_id", "sensors", "id"),
}


def create_rls_policy_direct(table_name: str) -> None:
    """Create RLS policy for tables with direct organization_id column."""
    # Enable RLS on the table
    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")

    # Force RLS for table owner as well
    op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")

    # Create policy for SELECT
    op.execute(f"""
        CREATE POLICY {table_name}_tenant_isolation_select ON {table_name}
        FOR SELECT
        USING (
            organization_id::text = current_setting('app.current_tenant_id', true)
            OR current_setting('app.bypass_rls', true) = 'true'
        )
    """)

    # Create policy for INSERT
    op.execute(f"""
        CREATE POLICY {table_name}_tenant_isolation_insert ON {table_name}
        FOR INSERT
        WITH CHECK (
            organization_id::text = current_setting('app.current_tenant_id', true)
            OR current_setting('app.bypass_rls', true) = 'true'
        )
    """)

    # Create policy for UPDATE
    op.execute(f"""
        CREATE POLICY {table_name}_tenant_isolation_update ON {table_name}
        FOR UPDATE
        USING (
            organization_id::text = current_setting('app.current_tenant_id', true)
            OR current_setting('app.bypass_rls', true) = 'true'
        )
        WITH CHECK (
            organization_id::text = current_setting('app.current_tenant_id', true)
            OR current_setting('app.bypass_rls', true) = 'true'
        )
    """)

    # Create policy for DELETE
    op.execute(f"""
        CREATE POLICY {table_name}_tenant_isolation_delete ON {table_name}
        FOR DELETE
        USING (
            organization_id::text = current_setting('app.current_tenant_id', true)
            OR current_setting('app.bypass_rls', true) = 'true'
        )
    """)


def create_rls_policy_indirect(table_name: str, fk_column: str, parent_table: str, parent_pk: str) -> None:
    """Create RLS policy for tables with indirect tenant relationship."""
    # Enable RLS on the table
    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")

    # Force RLS for table owner as well
    op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")

    # For sensors (linked to opc_servers which has organization_id)
    if parent_table == "opc_servers":
        tenant_check = f"""
            EXISTS (
                SELECT 1 FROM {parent_table}
                WHERE {parent_table}.{parent_pk} = {table_name}.{fk_column}
                AND {parent_table}.organization_id::text = current_setting('app.current_tenant_id', true)
            )
            OR current_setting('app.bypass_rls', true) = 'true'
        """
    # For readings and alerts (linked to sensors which is linked to opc_servers)
    else:
        tenant_check = f"""
            EXISTS (
                SELECT 1 FROM {parent_table}
                JOIN opc_servers ON opc_servers.id = {parent_table}.opc_server_id
                WHERE {parent_table}.{parent_pk} = {table_name}.{fk_column}
                AND opc_servers.organization_id::text = current_setting('app.current_tenant_id', true)
            )
            OR current_setting('app.bypass_rls', true) = 'true'
        """

    # Create policy for SELECT
    op.execute(f"""
        CREATE POLICY {table_name}_tenant_isolation_select ON {table_name}
        FOR SELECT
        USING ({tenant_check})
    """)

    # Create policy for INSERT
    op.execute(f"""
        CREATE POLICY {table_name}_tenant_isolation_insert ON {table_name}
        FOR INSERT
        WITH CHECK ({tenant_check})
    """)

    # Create policy for UPDATE
    op.execute(f"""
        CREATE POLICY {table_name}_tenant_isolation_update ON {table_name}
        FOR UPDATE
        USING ({tenant_check})
        WITH CHECK ({tenant_check})
    """)

    # Create policy for DELETE
    op.execute(f"""
        CREATE POLICY {table_name}_tenant_isolation_delete ON {table_name}
        FOR DELETE
        USING ({tenant_check})
    """)


def drop_rls_policies(table_name: str) -> None:
    """Drop all RLS policies and disable RLS for a table."""
    op.execute(f"DROP POLICY IF EXISTS {table_name}_tenant_isolation_select ON {table_name}")
    op.execute(f"DROP POLICY IF EXISTS {table_name}_tenant_isolation_insert ON {table_name}")
    op.execute(f"DROP POLICY IF EXISTS {table_name}_tenant_isolation_update ON {table_name}")
    op.execute(f"DROP POLICY IF EXISTS {table_name}_tenant_isolation_delete ON {table_name}")
    op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")


def upgrade() -> None:
    # Create RLS policy for opc_servers (direct organization_id)
    create_rls_policy_direct("opc_servers")

    # Create RLS policies for tables with indirect tenant relationship
    for table_name, (fk_column, parent_table, parent_pk) in INDIRECT_RLS_TABLES.items():
        create_rls_policy_indirect(table_name, fk_column, parent_table, parent_pk)


def downgrade() -> None:
    # Drop RLS policies in reverse order
    for table_name in reversed(RLS_TABLES):
        drop_rls_policies(table_name)
