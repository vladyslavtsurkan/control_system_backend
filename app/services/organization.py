import datetime
import uuid

from loguru import logger

from app.core.constants import PAGINATION_PER_PAGE
from app.core.exc import (
    AdminCanOnlyRemoveMembersException,
    CannotChangeOwnRoleException,
    CannotRemoveOwnerException,
    ObjectAlreadyExistsException,
    ObjectNotFoundException,
    OrganizationAccessDeniedException,
    OrganizationPermissionDeniedException,
    OwnerCannotLeaveException,
    RoleAlreadyAssignedException,
)
from app.enums import UserRoleInOrgEnum
from app.enums.audit_log import AuditActionEnum, AuditResourceTypeEnum
from app.schemas.base import PaginatedResponse
from app.schemas.organization import (
    ChangeRoleRequest,
    OrganizationCreateRequest,
    OrganizationMemberResponse,
    OrganizationUpdateRequest,
    OrganizationWithRoleResponse,
)
from app.schemas.user import UserResponse
from app.services.audit_log import AuditLogService
from app.uow.sql import SQLUnitOfWork


class OrganizationService:
    # Roles that have edit access (create, update, delete)
    EDIT_ROLES = {UserRoleInOrgEnum.owner, UserRoleInOrgEnum.admin}

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
                role=UserRoleInOrgEnum.owner,
            )
            await AuditLogService.log(
                uow=uow,
                organization_id=organization.id,
                actor=current_user,
                action=AuditActionEnum.created,
                resource_type=AuditResourceTypeEnum.organization,
                resource_id=organization.id,
                resource_name=organization.name,
            )
            logger.info(f"Organization created: {organization.name} by user: {current_user.email}")
            return OrganizationWithRoleResponse(
                id=organization.id,
                name=organization.name,
                description=organization.description,
                created_at=organization.created_at,
                role=UserRoleInOrgEnum.owner,
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
                raise OrganizationAccessDeniedException

            organization = await uow.organization.get({"id": organization_id, "deleted_at": None})
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

            updates = request.model_dump(exclude_unset=True)
            organization = await uow.organization.update(
                filters={"id": organization_id, "deleted_at": None},
                updates=updates,
            )
            if not organization:
                raise ObjectNotFoundException(id_=organization_id, model_name="Organization")

            await AuditLogService.log(
                uow=uow,
                organization_id=organization_id,
                actor=current_user,
                action=AuditActionEnum.updated,
                resource_type=AuditResourceTypeEnum.organization,
                resource_id=organization_id,
                resource_name=organization.name,
                metadata={"updates": updates},
            )
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
            await self._check_access(uow, current_user.id, organization_id, is_full_access=True)

            organization = await uow.organization.get({"id": organization_id, "deleted_at": None})
            if not organization:
                raise ObjectNotFoundException(id_=organization_id, model_name="Organization")

            await uow.organization.update(
                filters={"id": organization_id},
                updates={"deleted_at": datetime.datetime.now(datetime.UTC)},
            )
            await AuditLogService.log(
                uow=uow,
                organization_id=organization_id,
                actor=current_user,
                action=AuditActionEnum.deleted,
                resource_type=AuditResourceTypeEnum.organization,
                resource_id=organization_id,
                resource_name=organization.name,
            )
            logger.info(f"Organization deleted: {organization.name} by user: {current_user.email}")

    async def get_organization_members(
        self,
        uow: SQLUnitOfWork,
        current_user: UserResponse,
        organization_id: uuid.UUID,
        offset: int = 0,
        limit: int = PAGINATION_PER_PAGE,
    ) -> PaginatedResponse[OrganizationMemberResponse]:
        """Get all members of an organization. Any member can view."""
        async with uow:
            await self._check_membership(uow, current_user.id, organization_id)
            await self._check_org_exists(uow, organization_id)

            members, count = await uow.organization.get_organization_members(
                organization_id=organization_id, offset=offset, limit=limit
            )
            items = [
                OrganizationMemberResponse(
                    id=user.id,
                    email=user.email,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    created_at=user.created_at,
                    updated_at=user.updated_at,
                    role=role,
                )
                for user, role in members
            ]
            return PaginatedResponse[OrganizationMemberResponse](
                items=items,
                count=count,
                per_page=limit,
            )

    async def add_user_to_organization(
        self,
        uow: SQLUnitOfWork,
        current_user: UserResponse,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Add a user to an organization. Only owners and admins can add."""
        async with uow:
            await self._check_access(uow, current_user.id, organization_id)
            await self._check_org_exists(uow, organization_id)

            target_user = await uow.user.get({"id": user_id})
            if not target_user:
                raise ObjectNotFoundException(id_=user_id, model_name="User")

            existing_role = await uow.organization.get_user_role_in_organization(
                user_id=user_id, organization_id=organization_id
            )
            if existing_role is not None:
                raise ObjectAlreadyExistsException(id_=user_id, model_name="UserOrganizationAssociation")

            await uow.organization.add_user_to_organization(
                user_id=user_id, organization_id=organization_id, role=UserRoleInOrgEnum.member
            )
            await AuditLogService.log(
                uow=uow,
                organization_id=organization_id,
                actor=current_user,
                action=AuditActionEnum.member_added,
                resource_type=AuditResourceTypeEnum.member,
                resource_id=user_id,
                resource_name=target_user.email,
                metadata={"role": UserRoleInOrgEnum.member},
            )
            logger.info(f"User {user_id} added to organization {organization_id} by {current_user.email}")

    async def remove_user_from_organization(
        self,
        uow: SQLUnitOfWork,
        current_user: UserResponse,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """
        Remove a user from an organization. Owners can remove anyone (except owners).
        Admins can only remove members.
        """
        async with uow:
            caller_role = await self._check_access(uow, current_user.id, organization_id)
            await self._check_org_exists(uow, organization_id)

            target_role = await uow.organization.get_user_role_in_organization(
                user_id=user_id, organization_id=organization_id
            )
            if target_role is None:
                raise ObjectNotFoundException(id_=user_id, model_name="OrganizationMember")

            if target_role == UserRoleInOrgEnum.owner:
                raise CannotRemoveOwnerException

            if caller_role == UserRoleInOrgEnum.admin and target_role != UserRoleInOrgEnum.member:
                raise AdminCanOnlyRemoveMembersException

            await uow.organization.remove_user_from_organization(user_id=user_id, organization_id=organization_id)
            await AuditLogService.log(
                uow=uow,
                organization_id=organization_id,
                actor=current_user,
                action=AuditActionEnum.member_removed,
                resource_type=AuditResourceTypeEnum.member,
                resource_id=user_id,
                metadata={"removed_role": str(target_role)},
            )
            logger.info(f"User {user_id} removed from organization {organization_id} by {current_user.email}")

    async def leave_organization(
        self,
        uow: SQLUnitOfWork,
        current_user: UserResponse,
        organization_id: uuid.UUID,
    ) -> None:
        """Leave an organization. Owners cannot leave."""
        async with uow:
            role = await self._check_membership(uow, current_user.id, organization_id)
            await self._check_org_exists(uow, organization_id)

            if role == UserRoleInOrgEnum.owner:
                raise OwnerCannotLeaveException()

            await uow.organization.remove_user_from_organization(
                user_id=current_user.id, organization_id=organization_id
            )
            await AuditLogService.log(
                uow=uow,
                organization_id=organization_id,
                actor=current_user,
                action=AuditActionEnum.member_left,
                resource_type=AuditResourceTypeEnum.member,
                resource_id=current_user.id,
            )
            logger.info(f"User {current_user.email} left organization {organization_id}")

    async def change_member_role(
        self,
        uow: SQLUnitOfWork,
        current_user: UserResponse,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        request: ChangeRoleRequest,
    ) -> None:
        """
        Change a member's role. Only owners can change roles.
        When transferring ownership, the caller is demoted to admin.
        """
        async with uow:
            await self._check_access(uow, current_user.id, organization_id, is_full_access=True)
            await self._check_org_exists(uow, organization_id)

            if user_id == current_user.id:
                raise CannotChangeOwnRoleException

            target_role = await uow.organization.get_user_role_in_organization(
                user_id=user_id, organization_id=organization_id
            )
            if target_role is None:
                raise ObjectNotFoundException(id_=user_id, model_name="OrganizationMember")

            if target_role == request.role:
                raise RoleAlreadyAssignedException

            if request.role == UserRoleInOrgEnum.owner:
                # Transfer ownership: promote target to OWNER and demote caller to ADMIN
                await uow.organization.update_user_role(
                    user_id=user_id, organization_id=organization_id, role=UserRoleInOrgEnum.owner
                )
                await uow.organization.update_user_role(
                    user_id=current_user.id, organization_id=organization_id, role=UserRoleInOrgEnum.admin
                )
                await AuditLogService.log(
                    uow=uow,
                    organization_id=organization_id,
                    actor=current_user,
                    action=AuditActionEnum.role_changed,
                    resource_type=AuditResourceTypeEnum.member,
                    resource_id=user_id,
                    metadata={
                        "old_role": str(target_role),
                        "new_role": str(UserRoleInOrgEnum.owner),
                        "ownership_transferred": True,
                    },
                )
                logger.info(
                    f"Ownership of organization {organization_id} transferred "
                    f"from {current_user.email} to user {user_id}"
                )
            else:
                await uow.organization.update_user_role(
                    user_id=user_id, organization_id=organization_id, role=request.role
                )
                await AuditLogService.log(
                    uow=uow,
                    organization_id=organization_id,
                    actor=current_user,
                    action=AuditActionEnum.role_changed,
                    resource_type=AuditResourceTypeEnum.member,
                    resource_id=user_id,
                    metadata={"old_role": str(target_role), "new_role": str(request.role)},
                )
                logger.info(
                    f"User {user_id} role changed to {request.role} in organization "
                    f"{organization_id} by {current_user.email}"
                )

    @staticmethod
    async def _check_membership(
        uow: SQLUnitOfWork, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> UserRoleInOrgEnum:
        """Check if user is a member of the organization (any role)."""
        role = await uow.organization.get_user_role_in_organization(user_id=user_id, organization_id=organization_id)
        if role is None:
            raise OrganizationAccessDeniedException
        return role

    @staticmethod
    async def _check_org_exists(uow: SQLUnitOfWork, organization_id: uuid.UUID) -> None:
        """Check if the organization exists and is not soft-deleted."""
        organization = await uow.organization.get({"id": organization_id, "deleted_at": None})
        if not organization:
            raise ObjectNotFoundException(id_=organization_id, model_name="Organization")

    async def _check_access(
        self, uow: SQLUnitOfWork, user_id: uuid.UUID, organization_id: uuid.UUID, is_full_access: bool = False
    ) -> UserRoleInOrgEnum:
        """Check if user has access to the organization."""
        role = await uow.organization.get_user_role_in_organization(user_id=user_id, organization_id=organization_id)
        if role is None:
            raise OrganizationAccessDeniedException
        roles_to_check = self.EDIT_ROLES if not is_full_access else {UserRoleInOrgEnum.owner}
        if role not in roles_to_check:
            raise OrganizationPermissionDeniedException
        return role
