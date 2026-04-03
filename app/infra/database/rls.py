from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "set_tenant_context",
    "clear_tenant_context",
    "tenant_context",
    "set_rls_bypass",
    "RLS_TENANT_VAR",
    "RLS_BYPASS_VAR",
]

# PostgreSQL session variables for RLS
RLS_TENANT_VAR = "app.current_tenant_id"
RLS_BYPASS_VAR = "app.bypass_rls"


async def set_tenant_context(session: AsyncSession, tenant_id: UUID | str) -> None:
    """Set the current tenant context for RLS policies.

    Args:
        session: The SQLAlchemy async session.
        tenant_id: The UUID of the organization (tenant).

    Note:
        SET LOCAL doesn't support bound parameters in asyncpg, so we use
        string formatting after validating the UUID to prevent SQL injection.
    """
    # Validate UUID format to prevent SQL injection
    validated_tenant_id = str(UUID(str(tenant_id)))
    # Use string formatting since SET LOCAL doesn't support bound parameters
    await session.execute(text(f"SET LOCAL {RLS_TENANT_VAR} = '{validated_tenant_id}'"))


async def clear_tenant_context(session: AsyncSession) -> None:
    """Clear the tenant context.

    Args:
        session: The SQLAlchemy async session.
    """
    await session.execute(text(f"RESET {RLS_TENANT_VAR}"))


async def set_rls_bypass(session: AsyncSession, bypass: bool = True) -> None:
    """Enable or disable RLS bypass for superuser operations.

    Args:
        session: The SQLAlchemy async session.
        bypass: Whether to bypass RLS.
    """
    # Only allow 'true' or 'false' values
    bypass_value = "true" if bypass else "false"
    await session.execute(text(f"SET LOCAL {RLS_BYPASS_VAR} = '{bypass_value}'"))


@asynccontextmanager
async def tenant_context(session: AsyncSession, tenant_id: UUID | str) -> AsyncGenerator[None]:
    """Context manager for setting tenant context during a database operation.

    Usage:
        async with tenant_context(session, tenant_id):
            # All queries here will be filtered by tenant_id
            await session.execute(...)

    Args:
        session: The SQLAlchemy async session.
        tenant_id: The UUID of the organization (tenant).
    """
    await set_tenant_context(session, tenant_id)
    try:
        yield
    finally:
        await clear_tenant_context(session)
