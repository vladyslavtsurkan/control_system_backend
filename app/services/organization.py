import uuid

from loguru import logger

from app.core.constants import PAGINATION_PER_PAGE
from app.core.exc import ForbiddenException, ObjectNotFoundException
from app.enums import UserRoleInOrgEnum
from app.schemas.base import PaginatedResponse
from app.schemas.organization import (
    OrganizationCreateRequest,
    OrganizationUpdateRequest,
    OrganizationWithRoleResponse,
)
from app.schemas.user import UserResponse
from app.uow.sql import SQLUnitOfWork


class OrganizationService:
    # Roles that have edit access (create, update, delete)
    EDIT_ROLES = {UserRoleInOrgEnum.OWNER, UserRoleInOrgEnum.ADMIN}

    @staticmethod
    async def create_organization(
        uow: SQLUnitOfWork, current_user: UserResponse, request: OrganizationCreateRequest
    ) -> OrganizationWithRoleResponse:
        """Create a new organization and assign the creator as owner."""
        async with uow:
            organization = await uow.organization.create(request.model_dump())
            await uow.organization.add_user_to_organization(
                user_id=current_user.id,
                organization_id=organization.id,
                role=UserRoleInOrgEnum.OWNER,
            )
            logger.info(f"Organization created: {organization.name} by user: {current_user.email}")
            return OrganizationWithRoleResponse(
                id=organization.id,
                name=organization.name,
                description=organization.description,
                created_at=organization.created_at,
                role=UserRoleInOrgEnum.OWNER,
            )

    @staticmethod
    async def get_user_organizations(
        uow: SQLUnitOfWork, current_user: UserResponse, offset: int = 0, limit: int = PAGINATION_PER_PAGE
    ) -> PaginatedResponse[OrganizationWithRoleResponse]:
        """Get all organizations for the current user (paginated)."""
        async with uow:
            organizations, count = await uow.organization.get_user_organizations(
                user_id=current_user.id, offset=offset, limit=limit
            )
            items = [
                OrganizationWithRoleResponse(
                    id=org.id,
                    name=org.name,
                    description=org.description,
                    created_at=org.created_at,
                    role=role,
                )
                for org, role in organizations
            ]
            return PaginatedResponse[OrganizationWithRoleResponse](
                items=items,
                count=count,
                per_page=limit,
            )

    @staticmethod
    async def get_organization(
        uow: SQLUnitOfWork, current_user: UserResponse, organization_id: uuid.UUID
    ) -> OrganizationWithRoleResponse:
        """Get a specific organization if the user has access."""
        async with uow:
            role = await uow.organization.get_user_role_in_organization(
                user_id=current_user.id, organization_id=organization_id
            )
            if role is None:
                raise ForbiddenException("You don't have access to this organization")

            organization = await uow.organization.get({"id": organization_id, "is_deleted": False})
            if not organization:
                raise ObjectNotFoundException(id_=organization_id, model_name="Organization")

            return OrganizationWithRoleResponse(
                id=organization.id,
                name=organization.name,
                description=organization.description,
                created_at=organization.created_at,
                role=role,
            )

    async def update_organization(
        self,
        uow: SQLUnitOfWork,
        current_user: UserResponse,
        organization_id: uuid.UUID,
        request: OrganizationUpdateRequest,
    ) -> OrganizationWithRoleResponse:
        """Update an organization if the user has edit access."""
        async with uow:
            role = await self._check_access(uow, current_user.id, organization_id)

            organization = await uow.organization.update(
                filters={"id": organization_id, "is_deleted": False},
                updates=request.model_dump(exclude_unset=True),
            )
            if not organization:
                raise ObjectNotFoundException(id_=organization_id, model_name="Organization")

            logger.info(f"Organization updated: {organization.name} by user: {current_user.email}")
            return OrganizationWithRoleResponse(
                id=organization.id,
                name=organization.name,
                description=organization.description,
                created_at=organization.created_at,
                role=role,
            )

    async def delete_organization(
        self, uow: SQLUnitOfWork, current_user: UserResponse, organization_id: uuid.UUID
    ) -> None:
        """Soft delete an organization if the user is the owner."""
        async with uow:
            await self._check_access(uow, current_user.id, organization_id, is_deletion=True)

            organization = await uow.organization.get({"id": organization_id, "is_deleted": False})
            if not organization:
                raise ObjectNotFoundException(id_=organization_id, model_name="Organization")

            # Soft delete using the SoftDeleteMixin
            await uow.organization.update(
                filters={"id": organization_id},
                updates={"is_deleted": True},
            )
            logger.info(f"Organization deleted: {organization.name} by user: {current_user.email}")

    async def _check_access(
        self, uow: SQLUnitOfWork, user_id: uuid.UUID, organization_id: uuid.UUID, is_deletion: bool = False
    ) -> UserRoleInOrgEnum:
        """Check if user has access to the organization."""
        role = await uow.organization.get_user_role_in_organization(user_id=user_id, organization_id=organization_id)
        if role is None:
            raise ForbiddenException("You don't have access to this organization")
        roles_to_check = self.EDIT_ROLES if not is_deletion else {UserRoleInOrgEnum.OWNER}
        if role not in roles_to_check:
            raise ForbiddenException("You don't have permission to make this action on this organization")
        return role
