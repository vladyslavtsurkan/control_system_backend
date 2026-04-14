import uuid
from collections.abc import Sequence

from sqlalchemy import select, and_, Row, func, delete, update

from app.core.constants import PAGINATION_PER_PAGE
from app.enums import UserRoleInOrgEnum
from app.models import Organization, User
from app.models.user import UserOrganizationAssociation
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    model = Organization

    async def get_user_role_and_org_state(
        self,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> tuple[UserRoleInOrgEnum | None, bool]:
        """Return ``(role, is_active_org)`` for a user and organization in one query."""
        query = (
            select(UserOrganizationAssociation.role, Organization.deleted_at)
            .select_from(Organization)
            .outerjoin(
                UserOrganizationAssociation,
                and_(
                    UserOrganizationAssociation.organization_id == Organization.id,
                    UserOrganizationAssociation.user_id == user_id,
                ),
            )
            .where(Organization.id == organization_id)
        )
        row = (await self._session.execute(query)).first()
        if not row:
            return None, False
        role, deleted_at = row
        return role, deleted_at is None

    async def get_user_organizations(
        self, user_id: uuid.UUID, offset: int = 0, limit: int = PAGINATION_PER_PAGE
    ) -> tuple[Sequence[Row[tuple[Organization, UserRoleInOrgEnum]]], int]:
        """Get all organizations for a user with their roles (paginated)."""
        query = (
            select(Organization, UserOrganizationAssociation.role, func.count().over().label("total_count"))
            .join(UserOrganizationAssociation, Organization.id == UserOrganizationAssociation.organization_id)
            .where(
                and_(
                    UserOrganizationAssociation.user_id == user_id,
                    Organization.deleted_at.is_(None),
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
            user_id=user_id,
            organization_id=organization_id,
            role=role,
        )
        self._session.add(association)
        return association

    async def remove_user_from_organization(self, user_id: uuid.UUID, organization_id: uuid.UUID) -> None:
        """Remove a user from an organization."""
        stmt = delete(UserOrganizationAssociation).where(
            and_(
                UserOrganizationAssociation.user_id == user_id,
                UserOrganizationAssociation.organization_id == organization_id,
            )
        )
        await self._session.execute(stmt)

    async def get_organization_members(
        self, organization_id: uuid.UUID, offset: int = 0, limit: int = PAGINATION_PER_PAGE
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
        stmt = (
            update(UserOrganizationAssociation)
            .where(
                and_(
                    UserOrganizationAssociation.user_id == user_id,
                    UserOrganizationAssociation.organization_id == organization_id,
                )
            )
            .values(role=role)
            .returning(UserOrganizationAssociation)
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()
