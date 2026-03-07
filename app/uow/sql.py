from typing import Self
from uuid import UUID

from loguru import logger

from app.infra.database import get_session_maker, set_tenant_context, set_rls_bypass
from app.repositories import (
    OpcServerRepository,
    OrganizationRepository,
    CollectorApiKeyRepository,
    SensorRepository,
    ReadingRepository,
    AlertRuleRepository,
    AlertRepository,
    UserRepository,
)
from app.uow.base import ABCUnitOfWork


class SQLUnitOfWork(ABCUnitOfWork):
    def __init__(self, tenant_id: UUID | str | None = None, bypass_rls: bool = False) -> None:
        """
        Initialize the Unit of Work.

        Args:
            tenant_id: The organization ID for tenant isolation. If provided,
                      all queries will be filtered by this tenant.
            bypass_rls: If True, bypasses RLS policies (for admin operations).
        """
        self.session_maker = get_session_maker()
        self._tenant_id = tenant_id
        self._bypass_rls = bypass_rls

    async def __aenter__(self) -> Self:
        self.session = self.session_maker()

        # Set tenant context for RLS if tenant_id is provided
        if self._tenant_id:
            await set_tenant_context(self.session, self._tenant_id)

        # Set RLS bypass if needed (for admin operations)
        if self._bypass_rls:
            await set_rls_bypass(self.session, True)

        self.user = UserRepository(session=self.session)
        self.organization = OrganizationRepository(session=self.session)
        self.opc_server = OpcServerRepository(session=self.session)
        self.collector_api_key = CollectorApiKeyRepository(session=self.session)
        self.sensor = SensorRepository(session=self.session)
        self.reading = ReadingRepository(session=self.session)
        self.alert_rule = AlertRuleRepository(session=self.session)
        self.alert = AlertRepository(session=self.session)
        return self

    async def __aexit__(self, exc_type: any, exc: any, tb: any) -> None:
        if exc:
            logger.exception("An exception occurred during transaction: {exc}", exc=exc)
            await self.session.rollback()
        else:
            await self.session.commit()
        await self.session.close()
        await logger.complete()

        if exc:
            raise exc

    async def rollback(self):
        await self.session.rollback()

    async def set_tenant(self, tenant_id: UUID | str) -> None:
        """
        Set tenant context mid-transaction.

        Args:
            tenant_id: The organization ID for tenant isolation.
        """
        self._tenant_id = tenant_id
        await set_tenant_context(self.session, tenant_id)
