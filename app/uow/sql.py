from loguru import logger

from app.infra.database import get_session_maker
from app.uow.base import ABCUnitOfWork


class SQLUnitOfWork(ABCUnitOfWork):
    def __init__(self) -> None:
        self.session_maker = get_session_maker()

    async def __aenter__(self) -> "SQLUnitOfWork":
        self.session = self.session_maker()
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
