import uuid
from collections.abc import Sequence

from sqlalchemy import select, and_, Row, func

from app.enums import UserRoleInOrgEnum
from app.models import Organization, User
from app.models.user import UserOrganizationAssociation
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    model = Organization

    async def get_user_organizations(
        self, user_id: uuid.UUID, offset: int = 0, limit: int = 10
    ) -> tuple[Sequence[Row[tuple[Organization, UserRoleInOrgEnum]]], int]:
        """Get all organizations for a user with their roles (paginated)."""
        query = (
            select(Organization, UserOrganizationAssociation.role, func.count().over().label("total_count"))
            .join(UserOrganizationAssociation, Organization.id == UserOrganizationAssociation.organization_id)
            .where(
                and_(
                    UserOrganizationAssociation.user_id == user_id,
                    Organization.is_deleted.is_(False),
                )
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(query)
        rows = result.all()

        if rows:
            items = [(row[0], row[1]) for row in rows]
            total_count = rows[0][2]
        else:
            items = []
            total_count = 0

        return items, total_count

    async def get_user_role_in_organization(
        self, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> UserRoleInOrgEnum | None:
        """Get user's role in a specific organization."""
        query = select(UserOrganizationAssociation.role).where(
            and_(
                UserOrganizationAssociation.user_id == user_id,
                UserOrganizationAssociation.organization_id == organization_id,
            )
        )
        result = await self._session.execute(query)
        role = result.scalar_one_or_none()
        return role

    async def add_user_to_organization(
        self, user_id: uuid.UUID, organization_id: uuid.UUID, role: UserRoleInOrgEnum
    ) -> UserOrganizationAssociation:
        """Add a user to an organization with a specific role."""
        association = UserOrganizationAssociation(
            id=uuid.uuid4(),
            user_id=user_id,
            organization_id=organization_id,
            role=role,
        )
        self._session.add(association)
        return association

    async def remove_user_from_organization(self, user_id: uuid.UUID, organization_id: uuid.UUID) -> None:
        """Remove a user from an organization."""
        query = select(UserOrganizationAssociation).where(
            and_(
                UserOrganizationAssociation.user_id == user_id,
                UserOrganizationAssociation.organization_id == organization_id,
            )
        )
        result = await self._session.execute(query)
        association = result.scalar_one_or_none()
        if association:
            await self._session.delete(association)

    async def get_organization_members(
        self, organization_id: uuid.UUID, offset: int = 0, limit: int = 10
    ) -> tuple[Sequence[Row[tuple[User, UserRoleInOrgEnum]]], int]:
        """Get all members of an organization with their roles (paginated)."""
        query = (
            select(User, UserOrganizationAssociation.role, func.count().over().label("total_count"))
            .join(UserOrganizationAssociation, User.id == UserOrganizationAssociation.user_id)
            .where(UserOrganizationAssociation.organization_id == organization_id)
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(query)
        rows = result.all()

        if rows:
            items = [(row[0], row[1]) for row in rows]
            total_count = rows[0][2]
        else:
            items = []
            total_count = 0

        return items, total_count

    async def update_user_role(
        self, user_id: uuid.UUID, organization_id: uuid.UUID, role: UserRoleInOrgEnum
    ) -> UserOrganizationAssociation | None:
        """Update a user's role in an organization."""
        query = select(UserOrganizationAssociation).where(
            and_(
                UserOrganizationAssociation.user_id == user_id,
                UserOrganizationAssociation.organization_id == organization_id,
            )
        )
        result = await self._session.execute(query)
        association = result.scalar_one_or_none()
        if association:
            association.role = role
        return association
