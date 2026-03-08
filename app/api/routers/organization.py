import uuid

from fastapi import APIRouter, status

from app.api.dependencies import current_user, SQLUnitOfWorkDep, organization_service, offset_query, limit_query_default
from app.schemas import (
    PaginatedResponse,
    ChangeRoleRequest,
    OrganizationCreateRequest,
    OrganizationUpdateRequest,
    OrganizationWithRoleResponse,
    OrganizationMemberResponse,
)

__all__ = ["router"]

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post("/", response_model=OrganizationWithRoleResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    uow: SQLUnitOfWorkDep,
    user: current_user,
    request: OrganizationCreateRequest,
    service: organization_service,
):
    """Create a new organization. The creator becomes the owner."""
    return await service.create_organization(uow=uow, current_user=user, request=request)


@router.get("/", response_model=PaginatedResponse[OrganizationWithRoleResponse], status_code=status.HTTP_200_OK)
async def get_my_organizations(
    uow: SQLUnitOfWorkDep,
    user: current_user,
    service: organization_service,
    offset: int = offset_query,
    limit: int = limit_query_default,
):
    """Get all organizations the current user belongs to."""
    return await service.get_user_organizations(uow=uow, current_user=user, offset=offset, limit=limit)


@router.get("/{organization_id}", response_model=OrganizationWithRoleResponse, status_code=status.HTTP_200_OK)
async def get_organization(
    uow: SQLUnitOfWorkDep,
    user: current_user,
    organization_id: uuid.UUID,
    service: organization_service,
):
    """Get a specific organization by ID."""
    return await service.get_organization(uow=uow, current_user=user, organization_id=organization_id)


@router.patch("/{organization_id}", response_model=OrganizationWithRoleResponse, status_code=status.HTTP_200_OK)
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


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    uow: SQLUnitOfWorkDep,
    user: current_user,
    organization_id: uuid.UUID,
    service: organization_service,
):
    """Delete an organization. Only owners can delete."""
    await service.delete_organization(uow=uow, current_user=user, organization_id=organization_id)


@router.get(
    "/{organization_id}/members",
    response_model=PaginatedResponse[OrganizationMemberResponse],
    status_code=status.HTTP_200_OK,
)
async def get_organization_members(
    uow: SQLUnitOfWorkDep,
    user: current_user,
    organization_id: uuid.UUID,
    service: organization_service,
    offset: int = offset_query,
    limit: int = limit_query_default,
):
    """Get all members of an organization. Only members can view."""
    return await service.get_organization_members(
        uow=uow, current_user=user, organization_id=organization_id, offset=offset, limit=limit
    )


@router.post("/{organization_id}/add/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def add_user_to_organization(
    uow: SQLUnitOfWorkDep,
    user: current_user,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    service: organization_service,
):
    """Add a user to an organization. Only owners and admins can add."""
    await service.add_user_to_organization(uow=uow, current_user=user, organization_id=organization_id, user_id=user_id)


@router.post("/{organization_id}/remove/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_from_organization(
    uow: SQLUnitOfWorkDep,
    user: current_user,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    service: organization_service,
):
    """Remove a user from an organization. Only owners and admins can remove."""
    await service.remove_user_from_organization(
        uow=uow, current_user=user, organization_id=organization_id, user_id=user_id
    )


@router.post("/{organization_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_organization(
    uow: SQLUnitOfWorkDep,
    user: current_user,
    organization_id: uuid.UUID,
    service: organization_service,
):
    """Leave an organization. Owners cannot leave."""
    await service.leave_organization(uow=uow, current_user=user, organization_id=organization_id)


@router.patch("/{organization_id}/members/{user_id}/role", status_code=status.HTTP_204_NO_CONTENT)
async def change_member_role(
    uow: SQLUnitOfWorkDep,
    user: current_user,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    request: ChangeRoleRequest,
    service: organization_service,
):
    """
    Change a member's role. Only owners can change roles.
    When setting role to owner, ownership is transferred and the caller is demoted to admin.
    """
    await service.change_member_role(
        uow=uow, current_user=user, organization_id=organization_id, user_id=user_id, request=request
    )
