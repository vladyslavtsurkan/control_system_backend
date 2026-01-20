import uuid

from fastapi import APIRouter

from app.api.dependencies import current_user, SQLUnitOfWorkDep, organization_service, offset_query, limit_query
from app.schemas.base import PaginatedResponse
from app.schemas.organization import (
    OrganizationCreateRequest,
    OrganizationUpdateRequest,
    OrganizationWithRoleResponse,
)

__all__ = ["router"]

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post("/", response_model=OrganizationWithRoleResponse, status_code=201)
async def create_organization(
    uow: SQLUnitOfWorkDep,
    user: current_user,
    request: OrganizationCreateRequest,
    service: organization_service,
):
    """Create a new organization. The creator becomes the owner."""
    return await service.create_organization(uow=uow, current_user=user, request=request)


@router.get("/", response_model=PaginatedResponse[OrganizationWithRoleResponse], status_code=200)
async def get_my_organizations(
    uow: SQLUnitOfWorkDep,
    user: current_user,
    service: organization_service,
    offset: int = offset_query,
    limit: int = limit_query,
):
    """Get all organizations the current user belongs to."""
    return await service.get_user_organizations(uow=uow, current_user=user, offset=offset, limit=limit)


@router.get("/{organization_id}", response_model=OrganizationWithRoleResponse, status_code=200)
async def get_organization(
    uow: SQLUnitOfWorkDep,
    user: current_user,
    organization_id: uuid.UUID,
    service: organization_service,
):
    """Get a specific organization by ID."""
    return await service.get_organization(uow=uow, current_user=user, organization_id=organization_id)


@router.patch("/{organization_id}", response_model=OrganizationWithRoleResponse, status_code=200)
async def update_organization(
    uow: SQLUnitOfWorkDep,
    user: current_user,
    organization_id: uuid.UUID,
    request: OrganizationUpdateRequest,
    service: organization_service,
):
    """Update an organization. Only owners and admins can update."""
    return await service.update_organization(
        uow=uow, current_user=user, organization_id=organization_id, request=request
    )


@router.delete("/{organization_id}", status_code=204)
async def delete_organization(
    uow: SQLUnitOfWorkDep,
    user: current_user,
    organization_id: uuid.UUID,
    service: organization_service,
):
    """Delete an organization. Only owners can delete."""
    await service.delete_organization(uow=uow, current_user=user, organization_id=organization_id)
