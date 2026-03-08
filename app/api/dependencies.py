from typing import Annotated
from uuid import UUID

from fastapi import Depends, Query, Header

from app.core.constants import PAGINATION_PER_PAGE
from app.schemas import UserResponse
from app.services import (
    AlertRuleService,
    AuthService,
    CollectorService,
    UserService,
    OrganizationService,
    OpcServerService,
    SensorService,
    ReadingService,
    AlertService,
    TenantService,
)
from app.uow.sql import SQLUnitOfWork

__all__ = [
    "SQLUnitOfWorkDep",
    "user_service",
    "auth_service",
    "current_user",
    "collector_service",
    "organization_service",
    "opc_server_service",
    "sensor_service",
    "reading_service",
    "alert_service",
    "alert_rule_service",
    "offset_query",
    "limit_query_default",
    "limit_query_factory",
    "get_tenant_id",
    "get_tenant_uow",
    "TenantUnitOfWorkDep",
    "AdminUnitOfWorkDep",
    "TenantIdDep",
]

current_user = Annotated[UserResponse, Depends(AuthService.get_current_user)]

user_service = Annotated[UserService, Depends(UserService)]
auth_service = Annotated[AuthService, Depends(AuthService)]
collector_service = Annotated[CollectorService, Depends(CollectorService)]
organization_service = Annotated[OrganizationService, Depends(OrganizationService)]
opc_server_service = Annotated[OpcServerService, Depends(OpcServerService)]
sensor_service = Annotated[SensorService, Depends(SensorService)]
reading_service = Annotated[ReadingService, Depends(ReadingService)]
alert_service = Annotated[AlertService, Depends(AlertService)]
alert_rule_service = Annotated[AlertRuleService, Depends(AlertRuleService)]
tenant_service = Annotated[TenantService, Depends(TenantService)]


def limit_query_factory(max_limit: int = 100):
    """Factory for creating limit query parameters with a specified max limit."""

    return Query(PAGINATION_PER_PAGE, ge=1, le=max_limit, description=f"Number of items to return (max {max_limit})")


offset_query = Query(0, ge=0, description="Number of items to skip")
limit_query_default = limit_query_factory()


async def get_tenant_id(
    user: current_user,
    service: tenant_service,
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
) -> UUID:
    """Extract and validate tenant ID from X-Tenant-ID header."""
    return await service.validate_and_get_tenant_id(x_tenant_id=x_tenant_id, user=user)


def get_uow() -> SQLUnitOfWork:
    """Get a general Unit of Work without tenant scoping."""
    return SQLUnitOfWork()


def get_tenant_uow(
    tenant_id: UUID = Depends(get_tenant_id),
) -> SQLUnitOfWork:
    """Get a tenant-scoped Unit of Work."""
    return SQLUnitOfWork(tenant_id=tenant_id)


def get_admin_uow() -> SQLUnitOfWork:
    """Get a UnitOfWork that bypasses RLS for admin operations."""
    return SQLUnitOfWork(bypass_rls=True)


TenantIdDep = Annotated[UUID, Depends(get_tenant_id)]
SQLUnitOfWorkDep = Annotated[SQLUnitOfWork, Depends(get_uow)]
TenantUnitOfWorkDep = Annotated[SQLUnitOfWork, Depends(get_tenant_uow)]
AdminUnitOfWorkDep = Annotated[SQLUnitOfWork, Depends(get_admin_uow)]
