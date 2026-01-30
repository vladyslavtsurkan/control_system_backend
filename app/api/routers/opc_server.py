from uuid import UUID

from fastapi import APIRouter, status

from app.api.dependencies import (
    TenantUnitOfWorkDep,
    TenantIdDep,
    offset_query,
    limit_query,
    opc_server_service,
)
from app.schemas.base import PaginatedResponse
from app.schemas.opc_server import (
    OpcServerCreateRequest,
    OpcServerUpdateRequest,
    OpcServerResponse,
)

__all__ = ["router"]

router = APIRouter(prefix="/opc-servers", tags=["OPC Servers"])


@router.post("/", response_model=OpcServerResponse, status_code=status.HTTP_201_CREATED)
async def create_opc_server(
    uow: TenantUnitOfWorkDep,
    tenant_id: TenantIdDep,
    request: OpcServerCreateRequest,
    service: opc_server_service,
):
    """Create a new OPC server for the current tenant.

    Requires X-Tenant-ID header.
    """
    return await service.create_opc_server(uow=uow, tenant_id=tenant_id, request=request)


@router.get("/", response_model=PaginatedResponse[OpcServerResponse], status_code=status.HTTP_200_OK)
async def get_opc_servers(
    uow: TenantUnitOfWorkDep,
    service: opc_server_service,
    offset: int = offset_query,
    limit: int = limit_query,
):
    """Get all OPC servers for the current tenant.

    Requires X-Tenant-ID header. Results are automatically filtered by tenant.
    """
    return await service.get_opc_servers(uow=uow, offset=offset, limit=limit)


@router.get("/{server_id}", response_model=OpcServerResponse, status_code=status.HTTP_200_OK)
async def get_opc_server(
    uow: TenantUnitOfWorkDep,
    server_id: UUID,
    service: opc_server_service,
):
    """Get a specific OPC server by ID.

    Requires X-Tenant-ID header.
    """
    return await service.get_opc_server(uow=uow, server_id=server_id)


@router.patch("/{server_id}", response_model=OpcServerResponse, status_code=status.HTTP_200_OK)
async def update_opc_server(
    uow: TenantUnitOfWorkDep,
    server_id: UUID,
    request: OpcServerUpdateRequest,
    service: opc_server_service,
):
    """Update an OPC server.

    Requires X-Tenant-ID header.
    """
    return await service.update_opc_server(uow=uow, server_id=server_id, request=request)


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_opc_server(
    uow: TenantUnitOfWorkDep,
    server_id: UUID,
    service: opc_server_service,
):
    """Delete an OPC server (soft delete).

    Requires X-Tenant-ID header.
    """
    await service.delete_opc_server(uow=uow, server_id=server_id)
